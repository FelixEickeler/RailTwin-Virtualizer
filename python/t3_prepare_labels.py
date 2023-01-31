#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import argparse
import json
import math
import shutil
import uuid
from datetime import datetime
from itertools import cycle
from enum import Enum
from operator import itemgetter

from pathlib import Path
import numpy as np
import pandas
import re
import ifcopenshell

from .common.shared.algorithms.minimal_distance import refine_alignment, point2alignment_properties
from .common.shared.common.io import write
from .common.shared.common.logger import RailTwinLogger
from .labeling.elberink import dtm_analysis
from .common.shared.common.io import registered_reader, create_csv_reader
from .common.shared.common.io.pcs_formats import ModifiedHeliosFormat, CloudCompareExport
from .common.shared.algorithms.track_divider import track_divider
from .common.shared.common.io.io_options import IOOptions
from .common.shared.common.io.read_router import read_ply
from .modelling.oc_mapping import OCMapping
from collections import OrderedDict

logger = RailTwinLogger.create()
debug = False
force_mapping = True
force_system_mapping = True


class HeliosFrameConfiguration(Enum):
    basic = 10
    with_scanner_id = 11


def create_helios_header(configuration: HeliosFrameConfiguration):
    helios_header = {"X": np.float64,
                     "Y": np.float64,
                     "Z": np.float64,
                     "intensity": np.float64,
                     "echoWidth": np.float64,
                     "returnNumber": np.int32,
                     "numberOfReturns": np.int32,
                     "fullwaveIndex": np.int32,
                     "hitObjectId": np.int32,
                     "class": np.int32,
                     "gpsTime": np.float64,
                     }
    if configuration is HeliosFrameConfiguration.with_scanner_id:
        helios_header["source_leg"] = np.int32

    return helios_header


class DataSplits:

    def __init__(self, path, share):
        self.path = Path(path)
        self.share = share

    @staticmethod
    def dict2splits(base_path: Path, split_dict: {}):
        splits = []
        for name, val in split_dict.items():
            splits.append(DataSplits(base_path / name, val))
        return splits

    @staticmethod
    def single(base_path: Path):
        base_path = Path(base_path)
        return [DataSplits(base_path / "data", 100)]

    @staticmethod
    def dual_70_30(base_path: Path):
        base_path = Path(base_path)
        return [DataSplits(base_path / "training", 70),
                DataSplits(base_path / "testing", 30), ]

    @staticmethod
    def triple_60_20_20(base_path: Path):
        base_path = Path(base_path)
        return [DataSplits(base_path / "training", 60),
                DataSplits(base_path / "validation", 20),
                DataSplits(base_path / "testing", 20), ]

    @staticmethod
    def take_four(base_path: Path):
        base_path = Path(base_path)
        return [DataSplits(base_path / "quartile_0", 25),
                DataSplits(base_path / "quartile_1", 25),
                DataSplits(base_path / "quartile_2", 25),
                DataSplits(base_path / "quartile_3", 25)]

    @staticmethod
    def in_five(base_path: Path):
        base_path = Path(base_path)
        return [DataSplits(base_path / "quintile_0", 20),
                DataSplits(base_path / "quintile_1", 20),
                DataSplits(base_path / "quintile_2", 20),
                DataSplits(base_path / "quintile_3", 20),
                DataSplits(base_path / "quintile_4", 20)]


selector = {
    1: DataSplits.single,
    2: DataSplits.dual_70_30,
    3: DataSplits.triple_60_20_20,
    4: DataSplits.take_four,
    5: DataSplits.in_five
}


class PrepareLabels:
    _steps = ["batches", "enrich", "splits", "helios2rtib3+", "s3dis2rtib3+", "helios2s3dis", "unify_labels"]
    _default_batchsize = 100

    def __init__(self, _project):
        self.manual_mapping_path = None
        self.mapping_path = None
        self.project = _project
        if _project.label_input_path:
            self.input_path = _project.label_input_path.expanduser()
        else:
            raise FileNotFoundError("The label input path does not exist")

        if _project.label_output_path:
            self.output_path = _project.label_output_path.expanduser()
        else:
            self.output_path = self.input_path

        self.partition_func = selector[_project.partition] if _project.partition in selector else selector[1]

    def run(self):
        logger.info("Task 3: Preparing Labels")

        if self.project.step == "all_steps":
            steps = ["batches", "splits", "enrich", "helios2rtib3+"]
        # elif self.project.step == "al_real":
        #     steps = ["batchesCC", "extract_alignment", "splits", "enrich", "helios2s3dis"]
        else:
            steps = [self.project.step]

        # path shenanigans
        self.mapping_path = self.input_path / "global_object_mapping.json"
        if not self.mapping_path.exists():
            self.mapping_path = self.output_path / "global_object_mapping.json"
            mapping = OCMapping()
            mapping.save(self.mapping_path)
        global_mapping = OCMapping.read(self.mapping_path)

        system_component_mapping = None
        if self.project.system_component_mapping_path \
                and self.project.system_component_mapping_path.exists() \
                and not self.project.system_component_mapping_path.is_dir():
            self.system_component_mapping_path = self.project.system_component_mapping_path
            with open(self.system_component_mapping_path, "r") as mmf:
                system_component_mapping = json.load(mmf)
            system_component_mapping["path"] = self.system_component_mapping_path
        # with open(self.mapping_path, "r") as json_file:
        #     global_mapping = OCMapping(json_file)

        # reversed_mapping = {m["idx"]: {"uid": uid, "class_idx": m["class_idx"]} for uid, m in global_mapping["entities"].items()}

        if "batches" in steps:
            io_paths = self.update_io_paths("*.xyz")
            logger.info("Task 3.1: Creating Batches from Helios files")
            self.scanners2batches(io_paths, self.project.batch_size, mapping=global_mapping.idx2class)
            if self.output_path != self.input_path:
                shutil.copy(self.mapping_path, self.output_path / "global_object_mapping.json")
                alignment_folder = {bp.parent.parent for bp in io_paths.keys()}
                for af in alignment_folder:
                    files = [p for p in af.glob("*.*")]
                    for file in files:
                        shutil.copy(file, self.output_path / af.name / file.name)

                shutil.copy(self.mapping_path, self.output_path / "global_object_mapping.json")
                # now we need to update the io paths so they target the new location
                self.input_path = self.output_path

        if "enrich" in steps:
            logger.info("Task 3.2: Enriching Dataset")
            io_paths = self.update_io_paths("labels")
            alignment_folder = {bp.parent for bp in io_paths.keys()}
            for af in alignment_folder:
                alignment_path = [p for p in af.glob("*_local.csv")]
                if not alignment_path:
                    alignment_path = [p for p in af.glob("*.csv")]

                ipaths = [i for i in af.glob("./labels/batches/*.*") if i.suffix in registered_reader]
                if alignment_path:
                    self.enrich_point_properties(ipaths, alignment_path[0], 0b11)
                else:
                    logger.warn("Alignment was not found, falling back to above_ground only !")
                    self.enrich_point_properties(ipaths, None, 0b01)

        if "splits" in steps:
            logger.info("Task 3.3: Distributing Data")
            io_paths = self.update_io_paths("labels")
            alignment_folder = {bp.parent for bp in io_paths.keys()}
            for af in alignment_folder:
                ipaths = [i for i in af.glob("./labels/batches/*.*") if i.suffix in registered_reader]
                lout = af / "labels"
                splits = self.partition_func(lout)
                # This will allow custom splits
                # splits = DataSplits.dict2splits(lout, input_dict)
                self.split_batches(ipaths, splits)

        if "helios2s3dis" in steps:
            logger.info("3.4: Projecting to s3dis")
            self.output_path = self.output_path / "dataset_CCStyle"
            self.output_path.mkdir(parents=True, exist_ok=True)
            io_paths = self.update_io_paths("labels")
            alignment_folder = {bp.parent for bp in io_paths.keys()}
            class_mapping = {class_idx: class_name for class_name, class_idx in global_mapping["data"]["classes"].items()}
            if not self.output_path:
                raise AssertionError("No path given")
            for af in alignment_folder:
                for set in ["training", "validation", "testing"]:
                    self.helios2s3dis(src=af / "labels" / set,
                                      dst=self.output_path,
                                      track_name=af.name,
                                      class_mapping=class_mapping)

        if "helios2rtib3+" in steps:
            logger.info("3.4: Projecting to rtib3++")
            self.output_path = self.output_path
            self.output_path.mkdir(parents=True, exist_ok=True)
            io_paths = self.update_io_paths("labels")
            alignment_folder = {bp.parent for bp in io_paths.keys()}
            # class_mapping = {class_idx: class_name for class_name, class_idx in global_mapping["data"]["classes"].items()}
            if not self.output_path:
                raise AssertionError("No path given")

            # unified_mapping = None
            # if system_component_mapping:
            #     unified_mapping = self.unify_mapping(global_mapping, system_component_mapping, source_type="synthetic")

            for af in alignment_folder:
                folders = []
                label_folder = af / "labels"
                for s in ["quintile", "quartile"]:
                    folders = list(label_folder.glob(f"{s}_*"))
                    if folders:
                        break
                if not folders:
                    for s in ["training", "validation", "testing"]:
                        folders += list(label_folder.glob(f"{s}_*"))

                for set in folders:
                    self.helios2rtib3(src=af / "labels" / set, dst=self.output_path, track_name=af.name)

            # if system_component_mapping:
            #     with open(self.output_path / "metadata.json", "w") as f:
            #         json.dump(unified_mapping, f)
            # else:
            if not (self.output_path / "global_object_mapping.json").exists():
                shutil.copy(self.mapping_path, self.output_path / "global_object_mapping.json")

        if "s3dis2rtib3+" in steps:
            logger.info("3.X: Projecting s3dis to RailTwin")
            self.output_path = self.output_path
            self.output_path.mkdir(parents=True, exist_ok=True)
            area_paths = self.input_path.iterdir()
            file_type = CloudCompareExport
            reader_txt = create_csv_reader(file_type)
            if self.project.shift == True:
                iooptions = IOOptions.do_nothing()
                iooptions.binary = True
            else:
                iooptions = IOOptions.default()

            def convert(src):
                pattern = re.compile('([A-za-z\-]*)_(\d*)_?(\d{6})?.txt')
                collector = []
                for txt in src.glob("**/*.txt"):
                    if txt.stem == src.name:
                        continue
                    try:
                        data = reader_txt(txt)
                    except ValueError:
                        logger.warn(f"Value error: {txt}")
                        continue
                    # reproducible but unique id !

                    matches = pattern.match(txt.name)
                    if not matches:
                        logger.warn(f"Naming did not match the given standard {txt}")
                        continue

                    class_string = matches.group(1)
                    occurence = int(matches.group(2))
                    ident = str(txt.relative_to(self.input_path).parent / f"{class_string}_{occurence}")
                    data["uuid"] = ifcopenshell.guid.compress(uuid.uuid3(uuid.NAMESPACE_DNS, ident).hex)
                    data["src"] = ident
                    data["class_string"] = class_string
                    collector += [data]
                return collector

            # for area in area_paths:
            #     if not area.is_dir():
            #         continue
            #     collector = []
            #     sections = area.iterdir()
            #
            #     for section in sections:
            #         collector += convert(section)
            #
            #     if len(collector) == 0:
            #         continue
            #
            #     area_cloud = pandas.concat(collector)
            #     objects = area_cloud.drop_duplicates(subset=["uuid"])
            #     objects.apply(lambda obj: global_mapping.add_entity(obj["uuid"], obj["class_string"], str(Path(obj["src"]).parent)), axis=1)
            #
            #     # replace class idx & uuids
            #     area_cloud.replace({"class_string": global_mapping.data["classes"]}, inplace=True)
            #     area_cloud["object_id"] = area_cloud["uuid"].map(lambda uuid: global_mapping.data["entities"][uuid]["idx"])
            #     area_cloud.rename({"class_string": "class"}, inplace=True, axis='columns')
            #     area_cloud.drop(["uuid", "src", "scalar1", "scalar2"], axis=1, inplace=True)
            #
            #
            #     write((self.output_path / area.stem).with_suffix(".ply"), area_cloud, options=iooptions)
            #     # print(f"Beauty again! Area:{area.stem} => Obj=> {len(global_mapping.data['metadata']['distribution'])}")
            # global_mapping.save(self.output_path / "global_object_mapping.json")
            #
            # # now enrich properties
            # for area in area_paths:
            #     self.enrich_point_properties([(self.output_path / area.stem).with_suffix(".ply")], None, mode=self.project.enrichment_mode)

            # print(global_mapping.data['metadata']['distribution'])

        if "unify_labels" in steps:
            logger.info("3.X: Updating & Unifying labels")

            assert system_component_mapping
            source_type = self.project.sysco_type
            io_options = IOOptions.do_nothing()
            io_options.binary = True
            unified_mapping = self.unify_mapping(global_mapping, system_component_mapping, source_type=source_type)
            # output_path = self.output_path if self.output_path else self.input_path

            for ply_path in self.input_path.glob("**/*.ply"):
                logger.info(f"Unifying {ply_path}")
                data = read_ply(ply_path)
                data["component"] = data["class"].map(unified_mapping["component_mapping"])
                data["system"] = data["class"].map(unified_mapping["system_mapping"])
                data.drop(columns=["class"])
                if self.input_path == self.output_path:
                    protector = "_unified"
                else:
                    protector = ""
                out_path = self.output_path / (ply_path.parent / f"{ply_path.stem}{protector}.ply").relative_to(self.input_path)
                out_path.parent.mkdir(exist_ok=True, parents=True)
                write(out_path, data, io_options)

            if not debug:
                del (unified_mapping["component_mapping"])
                del (unified_mapping["system_mapping"])
            with open(self.output_path / "metadata.json", "w", encoding='utf-8') as f:
                unified_mapping["metadata"]["last_update"] = datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
                json.dump(unified_mapping, f, ensure_ascii=False, indent=4)

    def unify_mapping(self, global_mapping, system_component_mapping, source_type="synthetic"):
        # unified_mapping = None
        # if system_component_mapping:
        component_mapping = {}
        component_labels = {}
        component_distribution = {}
        system_distribution = {}
        system_mapping = {}
        system_labels = {}
        nr_of_components = 0
        changed_syco_mapping = False
        buffer_system_mapping = {}
        buffer_system_labels = {}

        for name, idx in global_mapping.data["classes"].items():
            if name in system_component_mapping[source_type]:
                unified_component_label = system_component_mapping[source_type][name]
            else:
                # print(f'"{name}": "{name}",')
                # logger.warn(f"The label {name} was not found in the physical mapping, will process by taking the concrete name! This should be fixed!")
                unified_component_label = name

            # now query with unified name !
            if not unified_component_label in system_component_mapping["component_labels"]:
                logger.warn(f"The component {unified_component_label} was not defined before, Please update the listing")
                system_component_mapping["component_labels"][unified_component_label] = len(system_component_mapping["component_labels"])
                changed_syco_mapping = True

            # generic mapping the idx of this mapping to the global id for this component
            component_mapping[idx] = system_component_mapping["component_labels"][unified_component_label]
            component_labels[unified_component_label] = system_component_mapping["component_labels"][unified_component_label]

            # agglomerate systems
            if unified_component_label in system_component_mapping["systems"]:
                system_name = system_component_mapping["systems"][unified_component_label]
                system_exists = True
            elif unified_component_label in system_component_mapping["system_labels"]:
                system_name = unified_component_label  # system_component_mapping["system_labels"][unified_component_label]
                system_exists = True
            else:
                system_name = unified_component_label
                system_exists = False

            if system_exists:
                if system_name not in system_component_mapping["system_labels"]:
                    # update sysco mapping
                    system_component_mapping["system_labels"][system_name] = len(system_component_mapping["system_labels"])
                    changed_syco_mapping = True
                system_mapping[idx] = system_component_mapping["system_labels"][system_name]
                system_labels[system_name] = system_component_mapping["system_labels"][system_name]
            else:
                if system_name not in buffer_system_labels:
                    buffer_system_labels[system_name] = len(buffer_system_mapping)
                idx_buffer = buffer_system_labels[system_name]
                buffer_system_mapping[idx] = idx_buffer
                system_mapping[idx] = 0
            try:
                component_distribution[unified_component_label] += global_mapping.data["metadata"]["distribution"][name]
            except KeyError:
                component_distribution[unified_component_label] = global_mapping.data["metadata"]["distribution"][name]
                # component_labels[unified_component_label] = len(component_labels)

            nr_of_components += global_mapping.data["metadata"]["distribution"][name]

        if force_system_mapping:
            next_entry = max([i for i in system_mapping.values()]) + 1
            for idx, idx_buffer in buffer_system_mapping.items():
                system_mapping[idx] = idx_buffer + next_entry
            for name, idx_buffer in buffer_system_labels.items():
                system_labels[name] = idx_buffer + next_entry

        updated_entities = {}
        for uid, inner in global_mapping.data["entities"].items():
            inner["class_idx"] = component_mapping[inner["class_idx"]]
            updated_entities[uid] = inner

        # historgram systems
        systogram = {}
        inv_sys_labels = {value: key for key, value in system_labels.items()}
        for idx, sys_idx in system_mapping.items():
            class_name = global_mapping.reverse_classes[idx]
            system_name = inv_sys_labels[sys_idx]
            try:
                systogram[system_name] += global_mapping.data["metadata"]["distribution"][class_name]
            except KeyError:
                systogram[system_name] = global_mapping.data["metadata"]["distribution"][class_name]

        # Order for output
        system_labels = OrderedDict(sorted(system_labels.items(), key=itemgetter(1)))
        component_labels = OrderedDict(sorted(component_labels.items(), key=itemgetter(1)))
        systogram = OrderedDict(sorted(systogram.items(), key=itemgetter(1), reverse=True))
        component_distribution = OrderedDict(sorted(component_distribution.items(), key=itemgetter(1), reverse=True))

        unified_mapping = {
            "metadata": {
                "guid": str(uuid.uuid4()),
                "number_of_component_classes": len(component_mapping),
                "number_of_system_classes": len(system_mapping),
                "number_of_component": nr_of_components,
                "last_update": datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),
                "systogram": systogram,
                "component_distribution": component_distribution,

            },
            "component_labels": system_component_mapping["component_labels"],
            "system_labels": system_component_mapping["system_labels"],
            "component_mapping": component_mapping,
            "system_mapping": system_mapping,
            "sources": global_mapping.data["sources"],
            "entities": updated_entities
        }

        if changed_syco_mapping and force_mapping:
            syco_path = system_component_mapping["path"]
            del system_component_mapping["path"]
            with open(syco_path, 'w', encoding='utf-8') as f:
                system_component_mapping["metadata"]["last_update"] = datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
                json.dump(system_component_mapping, f, ensure_ascii=False, indent=4)

        return unified_mapping

    def update_io_paths(self, target="*/*.xyz"):
        io_paths = {}
        # print(self.input_path)
        for cp in self.input_path.glob(f"*/{target}"):
            if cp != self.input_path:
                io_paths[cp] = self.output_path / cp.parent.relative_to(self.input_path) / "labels"
            else:
                io_paths[cp] = self.output_path / "labels"
        return io_paths

    def scanners2batches(self, io_paths, batch_size, mapping):
        """
        Takes a big combined simulation file and splits it via pca into multiple smaller parts.
        :param io_paths: A dictionary where the key is the input and the value is the output path
        :param batch_size: Max size of the PCA cut. If bigger, part will be split equally
        :param mapping: : This will map the object to the ifc type and also the class.
        """
        # registered the "xyz" to be used in the division
        mhf = ModifiedHeliosFormat(object_mapping=mapping)
        registered_reader[".xyz"] = create_csv_reader(format=mhf)
        io_options = IOOptions.do_nothing()
        io_options.filetype = ".ply"
        io_options.binary = True
        in_options = IOOptions.do_nothing()
        in_options.intensity = "normalize"
        for ipath, opath in io_paths.items():
            all_batches_path = opath / "batches"
            all_batches_path.mkdir(exist_ok=True, parents=True)
            track_divider(src=ipath, dst=all_batches_path, length=batch_size, out_options=io_options, in_options=in_options, transformer=mhf, label="batch")

    def enrich_point_properties(self, input_paths, alignment_path, mode=0b11, inplace=False):
        if mode != 0:
            refined_alignment = None
            if mode & 2:
                alignment = pandas.read_csv(alignment_path)
                refined_alignment = refine_alignment(alignment, 100)  # resample 100 points per

            io_options = IOOptions.do_nothing()
            io_options.xyz_accuracy = "<f4"
            io_options.binary = True

            leni = len(input_paths)
            for i, path in enumerate(input_paths):
                logger.info(f"Now complementing ({i + 1}/{leni}: {path}")
                point_cloud = read_ply(path)

                # Elberink2013 dtm height !s
                if mode & 1:
                    logger.info(f"Staring DTM Enrichment")
                    dtm_analysis(point_cloud, inplace=True, debug=debug)

                # 3 Alignment based props: distance, angle, ....
                if mode & 2:
                    logger.info(f"Staring Alignment based Enrichment")
                    point2alignment_properties(point_cloud, refined_alignment, inplace=True)

                outpath = path
                if not inplace:
                    cf_name = path.parent.stem
                    out_folder = path.parent.parent / f"{cf_name}_enrichted"
                    out_folder.mkdir(exist_ok=True)
                    outpath = out_folder / path.name

                write(outpath, point_cloud, io_options)

    def split_batches(self, input_paths, splits: [DataSplits]):
        """
        Methods to distribute the batches between multiple buckets e.g. train, validation, and testing.
        :param input_paths: list of all paths
        :param splits: Splits object that contains the buckets and splits.
        :return:
        """
        batches = [p.resolve() for p in input_paths]
        splits.sort(key=lambda s: s.share)
        lcm = math.gcd(*[s.share for s in splits])

        full_takeaway = []
        for s in splits:
            s.chunk_size = int(s.share / lcm)
            for in_one_go in range(s.chunk_size):
                full_takeaway.append(s.path)

            # will throw if exists already
            # TODO add a log
            # logger = self.project.logger
            try:
                s.path.mkdir(parents=True, exist_ok=True)
            except FileExistsError:
                # TODO Logger
                files = s.path.glob("**/*.*")
                if any(files):
                    raise FileExistsError("Folder {} is not empty!".format(s.path))

        full_takeaway = cycle(full_takeaway)
        for batch in batches:
            target = next(full_takeaway)
            shutil.copy(batch, target / "{}_{}".format(target.relative_to(target.parent), batch.name))

    def helios2s3dis(self, src, dst, track_name, class_mapping):
        logger.info(f"Converting {src.name} to CC export style!")
        logger.trace("Source_path:{}".format(src))
        logger.trace("Target_path:{}".format(dst))
        area = f"{track_name}_{src.name}"
        dst = dst / area

        for ply_file in src.glob("*.ply"):
            section_number = ply_file.stem[-3:]
            section_dst = dst / f"section_{section_number}" / "Annotations"
            section_dst.mkdir(exist_ok=True, parents=True)
            data = read_ply(ply_file)
            objects = [y for x, y in
                       data[["x", "y", "z", "above_ground", "intensity", "DTMAnalysis", "object_id", "class"]].groupby('object_id', as_index=False)]

            object_counter = {}
            for object in objects:
                if len(object) < 2:
                    continue
                class_idx = object.iloc[0]["class"]
                class_name = class_mapping[class_idx]
                try:
                    object_counter[class_name] += 1
                except KeyError:
                    object_counter[class_name] = 0

                dst_path = section_dst / f"{class_name}_{object_counter[class_name]}.txt"
                np.savetxt(dst_path, object, delimiter=" ")

    def helios2rtib3(self, src, dst, track_name):
        logger.trace("Source_path:{}".format(src))
        logger.trace("Target_path:{}".format(dst))
        area = f"{track_name}_{src.name}"
        dst = dst / f"{track_name}" / area
        dst.parent.mkdir(exist_ok=True)

        collector = []
        for ply_file in src.glob("*.ply"):
            section_number = ply_file.stem[-3:]
            dat = read_ply(ply_file)
            dat["section_number"] = section_number
            collector += [dat.loc[:, ["x", "y", "z", "above_ground", "intensity", "class", "object_id"]]]

        out_data = pandas.concat(collector)

        # unify mappings !
        # out_data["component"] = out_data["class"].map(mapping["component_mapping"])
        # out_data["system"] = out_data["class"].map(mapping["system_mapping"])
        # out_data.drop(["class"], axis=1)
        options = IOOptions.do_nothing()
        options.binary = True
        write(dst.with_suffix(".ply"), out_data, options=options)

    @staticmethod
    def add_parser_options(subparser: argparse.PARSER):
        pla_parser = subparser.add_parser("prepare_labels")
        pla_parser.add_argument('--step', choices=PrepareLabels._steps + ["all_steps"], help="[splits, batches, kpconv]",
                                required=False, dest="secondary")
        pla_parser.add_argument('--batch_size', type=int,
                                help="Fused scanner files. If you simmulation resolves with 1m "
                                     "=> 50 will result in 50m batches",
                                default=PrepareLabels._default_batchsize)
        pla_parser.add_argument('--partition', type=int, help="1 -> 60-20-20; 2 -> 70-30; validation:20}", default=1)
        pla_parser.add_argument('--in', type=Path, dest="label_input_path",
                                help="File or folder containing multiple *.xyz files from helios",
                                required=True)
        pla_parser.add_argument('--out', type=Path, dest="label_output_path",
                                help="Folder to output batches, splits or kpconv plys", default=None,
                                required=False)
        pla_parser.add_argument('--recursive', type=Path,
                                help="Recursivly will process the input path, only valid for "
                                     "kpconv option.", required=False, default=True)
        # pla_parser.add_argument('--classes', type=Path, required=False, default="")
        pla_parser.add_argument('--grouping', type=Path, required=False, dest="group_obj")
        pla_parser.add_argument('--no_shift', required=False, dest="shift", action='store_true')
        pla_parser.add_argument("--sysco_map", type=Path, required=False, dest="system_component_mapping_path",
                                default=Path(__file__).parent / "labeling" / "mappings" / "rtsysco_mapping.json")
        pla_parser.add_argument("--sysco_type", type=str, required=False, dest="sysco_type", default="synthetic")
        pla_parser.add_argument("--enrichment_mode", type=int, required=False, dest="enrichment_mode", default=0b11)
        return pla_parser

# TODO
# merge file to 50m chunks => TEST
# clean up additional points from the angle => not implemented
# save and distribute => TEST
# merge files => TEST
# group object => TEST
# prepare for s3dsim. => skipped to work on ply directly
