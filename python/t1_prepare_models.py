#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import json
import multiprocessing
import os
import shutil
import stat
import uuid
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import numpy as np
import pandas
import spdlog as spd

from python.modelling.oc_mapping import OCMapping
from python.modelling.openshell_helpers import IfcFileContainer, clone_into
from .common.docker_helpers import docker_run, create_docker
from .modelling.alignment_shapes.alignment import Alignment
from .modelling.blender.texture_modifier import create_augmentations

# Global Variables
ONLY_CREATE_ONE_MODEL_MULTI_TRACKS = False
MAX_CPU_COUNT = 8
BLENDER_VOXEL_SIZE = 0.16


class PrepareModels:
    _steps = ["extract_alignment", "extract_areas", "convert", "helios_prep", "model_evaluation"]

    def __init__(self, _project):
        self.project = _project
        # This is a double definition with the parser !
        self.plot = self.project.plot if hasattr(_project, "plot") else True
        self.show_plot = self.project.show_plot if hasattr(_project, "show_plot") else False
        self.resolution = self.project.trajectory_resolution if hasattr(_project, "trajectory_resolution") else 1  # in m

        ifc_input_path = self.project.ifc_input_path.expanduser()

        if ifc_input_path.is_dir():
            self.inputs = list(ifc_input_path.glob("*.ifc")) + list(ifc_input_path.glob("*.IFC"))
            self.inputs.sort()
        else:
            if ifc_input_path.exists():
                self.inputs = [ifc_input_path]
            else:
                raise FileNotFoundError("The provided model_path was not found")

        if hasattr(self.project, "model_output_path") and self.project.model_output_path is not None:
            model_output_path = self.project.model_output_path.expanduser()
            if model_output_path.exists() and not model_output_path.is_dir():
                raise FileExistsError("Cannot overwrite file with a folder")
            else:
                model_output_path.mkdir(parents=True, exist_ok=True)
                self.output = model_output_path
        else:
            self.output = ifc_input_path

        if not self.project.object_mapping:
            self.project.object_mapping = self.output / "global_object_mapping.json"
        self.project.object_mapping = self.project.object_mapping.expanduser()

    def run(self):
        self.project.logger.set_level(spd.LogLevel.INFO)

        # step mode
        if self.project.step == "all_steps":
            steps = PrepareModels._steps
        else:
            steps = self.project.step

        self.project.logger.debug(f"Files to process: {[str(i) for i in self.inputs]}")
        self.project.logger.debug(f"{self.output}")

        if "extract_alignment" in steps:
            self.project.logger.info("Extracting Alignments !")
            for process_file_count, ifc_file_path in enumerate(self.inputs):
                discrete_alignments_paths = []
                ifc_file = ifcopenshell.open(ifc_file_path)
                self.project.logger.info(f"Processing IFC-Files: {ifc_file_path.name}")
                ifc_alignments = ifc_file.by_type('IfcAlignment')
                collection = []
                for align in ifc_alignments:
                    _alignment = Alignment()
                    if not _alignment.parse(align.Axis): continue
                    collection.append(_alignment)
                self.project.logger.trace(f"Alignments collected. Found: {len(collection)}")
                clean_collection = {}
                for a in collection:
                    if a.name not in clean_collection and a.name is not None:
                        clean_collection[a.name] = a
                self.project.logger.trace(f"Alignments cleaned! LeftOvers: {clean_collection}")

                data = {
                    "horizontal_mapping": {},
                    "vertical_mapping": {}
                }
                collector = []
                folder_path = _outpath = self.output / f"{ifc_file_path.stem}"
                for a in clean_collection.values():
                    a.horizontal_mapping = data["horizontal_mapping"]
                    a.vertical_mapping = data["vertical_mapping"]
                    _outpath = folder_path / ("#{}_{:3.2f}".format(a.name, self.project.trajectory_resolution)).replace(".", "m")
                    _outpath.parent.mkdir(parents=True, exist_ok=True)

                    if self.plot:
                        self.project.logger.trace(f"Plotting: {a.name}")
                        a.plot(path=_outpath.with_suffix(".svg"), show=self.show_plot)
                    self.project.logger.trace(f"Sampling: {a.name}")
                    points = a.sample(self.project.trajectory_resolution)
                    _outpath = _outpath.with_suffix(".csv")
                    points.to_csv(_outpath, index=False)
                    discrete_alignments_paths.append(_outpath)
                    collector.append(points)

                    # ensure consecutive type naming
                    data["horizontal_mapping"] = a.horizontal_mapping
                    data["vertical_mapping"] = a.vertical_mapping
                    a.to_json(_outpath.with_suffix(".json"))

                with open(folder_path / f"{ifc_file_path.stem}_metadata.json", "w") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

                if collector:
                    pointer_hseg = 0
                    pointer_vseg = 0

                    for df in collector:
                        df["segment_horizontal"] += pointer_hseg
                        df["segment_vertical"] += pointer_vseg
                        pointer_hseg = df["segment_horizontal"].max()
                        pointer_vseg = df["segment_vertical"].max()

                    combined = pandas.concat(collector)
                    combined_path = folder_path / f"combined_{ifc_file_path.stem}.ccsv"
                    combined.to_csv(combined_path, index=False)
                    # plot
                    points = Alignment.from_csv(combined_path)
                    comb_alignment_name = f"All Alignments {ifc_file_path.stem}"
                    if self.plot:
                        self.project.logger.trace(f"Plotting: {comb_alignment_name}")
                        Alignment._plot(df=points, path=combined_path.with_suffix(".svg"), show=self.show_plot, name=comb_alignment_name)

                del _outpath
                del ifc_alignments
                del collection
                del clean_collection
        if "extract_areas" in steps:
            self.project.logger.info("Extracting IFC Areas / Content !")
            global_mapping = OCMapping.read(self.project.object_mapping)
            discrete_alignments_paths = self.output.glob("**/*.csv")
            input_map = {ifc.stem: ifc for ifc in self.inputs}

            file_tree = {}
            for da in discrete_alignments_paths:
                # ifc_file_stem, alignment_name = da.parent.stem.split("==")
                ifc_file_stem = da.parent.name
                if ifc_file_stem in input_map:
                    try:
                        file_tree[ifc_file_stem].append(da)
                    except KeyError:
                        file_tree[ifc_file_stem] = [da]

            for process_file_count, ifc_file_stem in enumerate(file_tree.keys()):
                # self.project.logger.info(f"Separating different areas of: {ifc_file_stem}")
                self.project.logger.info(f"Preparing the IFC-File for further processing: {ifc_file_stem}")

                ifc_file_path = input_map[ifc_file_stem]
                ifc_file = ifcopenshell.open(ifc_file_path)

                # setup buckets for splits named IfcFileContainer
                file_containers = []
                samples = []
                for current_alignment_path in file_tree[ifc_file_stem]:
                    # name = current_alignment_path.stem.split("#")[-1].split("_")[0]
                    samples.append(Alignment.from_csv(current_alignment_path))
                samples = pandas.concat(samples)
                folder = file_tree[ifc_file_stem][0].parent.stem
                bounding_box = (
                    (float(samples["x"].min() - 200), float(samples["y"].min() - 200), float(samples["z"].min() - 50)),
                    (float(samples["x"].max() + 200), float(samples["y"].max() + 200), float(samples["z"].max() + 50))
                )
                file_containers.append(IfcFileContainer(name=ifc_file_stem,
                                                        path=self.output / folder / f"{ifc_file_stem}.csv",
                                                        bounding_box=bounding_box,
                                                        template=ifc_file))

                settings = ifcopenshell.geom.settings()
                settings.set(settings.USE_WORLD_COORDS, True)
                iterator = ifcopenshell.geom.iterator(settings, ifc_file, min(multiprocessing.cpu_count(), MAX_CPU_COUNT))
                not_in_any_alignment_container = IfcFileContainer(name="NotInAlignment",
                                                                  path=self.output / ("{}=>#{}_{:3.2f}".format(
                                                                      ifc_file_path.stem, "NotAlignment",
                                                                      self.project.trajectory_resolution)).replace(".", "m"),
                                                                  bounding_box=((0, 0, 0), (0, 0, 0)),
                                                                  template=ifc_file)

                tmp_geo_repr_context = ifc_file.by_type("IfcGeometricRepresentationContext")
                if len(tmp_geo_repr_context) == 1:
                    geo_repr_context = tmp_geo_repr_context[0]
                else:
                    geo_repr_context = ifc_file.create_entity("IfcGeometricRepresentationContext")
                    raise NotImplementedError("This is not done correctly !")
                del tmp_geo_repr_context

                # unwrap mapped items and convert breps
                self.project.logger.info("TriangulSeperationAtion ...")

                if iterator.initialize():
                    while True:
                        shape = iterator.get()
                        source_element = ifc_file.by_guid(shape.guid)

                        # This is very specific to the IFC-File we are working with that were exported from ProVI.
                        # Sleepers in switches (german := "Weiche") are exported as one entity.
                        # Therefore, we check the single entities and separate them.

                        if source_element.Name == "Weiche":
                            # count number of instances from the triangulated face list and clone them
                            # remove other instances of the tf-faces
                            # run create shapes to get the lists in global space
                            # name after class of objects (maybe also get lenght for sleeper for grouping)
                            tesselated_geometries = source_element.Representation.Representations[0].Items
                            elements = []
                            obj_vertices = []
                            obj_faces = []
                            for i, tfs in enumerate(tesselated_geometries):
                                if not tfs.is_a('IfcTriangulatedFaceSet'):
                                    print("The representation of Weiche was not a IfcTriangulatedFaceSet")
                                    print(f"Type : {tfs.is_a()}")
                                    print(f"In SourceElement : {source_element.GlobalId}, source_element.")

                                # very wastefull, as this recreates the geometries n times for nothing.
                                # However, recreating everything from scratch needs more care than I can give right now.
                                copy = clone_into(ifc_file, ifc_file, source_element)
                                for ctfs in copy.Representation.Representations[0].Items:
                                    ifc_file.remove(ctfs)
                                copy.Representation.Representations[0].Items = [tfs]
                                if len(tfs.CoordIndex) == 12:
                                    coordinates = np.array(tfs.Coordinates[0])
                                    sleeper_width = np.linalg.norm(coordinates[1] - coordinates[0])
                                    sleeper_length = np.linalg.norm(coordinates[2] - coordinates[1])
                                    if sleeper_width < 2.61:
                                        copy.Name = "Schwelle_Weiche_Becken"
                                    else:
                                        copy.Name = "Schwelle_Weiche_Herz"
                                else:
                                    copy.Name = "Schiene_Weiche"

                                copy.GlobalId = ifcopenshell.guid.compress(uuid.uuid1().hex)

                                shape = ifcopenshell.geom.create_shape(settings, copy)
                                elements.append(copy)
                                obj_vertices.append(np.reshape(np.array(shape.geometry.verts), (-1, 3)))
                                obj_faces.append(np.reshape(np.array(shape.geometry.faces, dtype=int), (-1, 3)))
                        else:
                            verts = shape.geometry.verts  # X Y Z of vert [flat representation]
                            np_verts = np.reshape(np.array(verts), (-1, 3))
                            # materials = shape.geometry.materials  # Material names and colour style information that are relevant to this shape
                            # material_ids = shape.geometry.material_ids  # Indices of material applied per triangle face e.g. [f1m, f2m, ...]
                            flat_faces = shape.geometry.faces  # tuple of faces [flat representation]
                            faces = np.reshape(np.array(flat_faces, dtype=int),
                                               (-1, 3))  # Indices of vertices per triangle face e.g. [f1v1, f1v2, f1v3, f2v1, f2v2, f2v3, ...]

                            if source_element.Name.find("Fahrdraht") != -1:
                                # It's a Fahrdraht and needs to be changed.
                                vertices = pandas.DataFrame(np_verts, columns=["x", "y", "z"])
                                means = vertices.mean()
                                vertices -= means
                                U, s, V = np.linalg.svd(vertices)
                                # constructor = source_element.__dict__
                                # del constructor["type"]
                                # ifc_file.create_entity("IfcBuildingElementProxy", **constructor)

                                # # Debug and data stuff
                                # linepts = V[0] * np.mgrid[-100:100:2j][:, np.newaxis]
                                # # linepts += means
                                #
                                # linepts2 = V[1] * np.mgrid[-1:1:2j][:, np.newaxis]
                                # # linepts2 += means
                                #
                                # import matplotlib.pyplot as plt
                                # import mpl_toolkits.mplot3d as m3d
                                #
                                # ax = m3d.Axes3D(plt.figure())
                                # ax.scatter3D(*vertices.to_numpy().T)
                                # ax.plot3D(*linepts.T)
                                # ax.plot3D(*linepts2.T, color='red')
                                # plt.show()
                                #
                                v_diff = np.array([1, 1, 1]).dot(V.T)
                                transformed_vertices = np.dot(vertices, np.sign(v_diff) * V.T)

                                # get heights of vertices and apply thresholds, care ifc starts with 1 not 0
                                # gfaces = faces
                                # gverts = np_verts

                                v2_heights = transformed_vertices[faces, 1]  # get the vertice v2 for each face
                                tags = np.zeros_like(v2_heights)
                                thr_cw = v2_heights.min() + 0.044  # contact_wire
                                thr_mw = v2_heights.max() - 0.044  # messenger_wire (!sic)
                                tags[v2_heights < thr_cw] = -1
                                tags[v2_heights > thr_mw] = 1
                                face_value = tags.sum(axis=1)  # which axis ?

                                # place faces into new bins, could be numpy
                                face_bins = [[], [], []]
                                for i, face in enumerate(face_value):
                                    if face == -3:
                                        face_bins[0].append(i)
                                    elif face == 3:
                                        face_bins[2].append(i)
                                    else:
                                        face_bins[1].append(i)

                                # cw, dropper, mw
                                elements = [source_element, clone_into(ifc_file, ifc_file, source_element), clone_into(ifc_file, ifc_file, source_element)]

                                # The fahrdraht will keep the name (as its actually correct, and also the ifc id)
                                # elements[0].Name = source_element.Name # Fahrdraht is actually correct
                                # elements[0].Name = source_element.GlobaId
                                styles = elements[0].Representation.Representations[0].Items[0].StyledByItem

                                elements[1].Name = source_element.Name.replace("Fahrdraht", "Hänger")
                                elements[1].GlobalId = ifcopenshell.guid.compress(uuid.uuid1().hex)
                                dropper_style = clone_into(ifc_file, ifc_file, styles)[0]
                                dropper_style.Item = elements[1].Representation.Representations[0].Items[0]

                                elements[2].Name = source_element.Name.replace("Fahrdraht", "Tragseil")
                                elements[2].GlobalId = ifcopenshell.guid.compress(uuid.uuid1().hex)
                                messenger_wire_style = clone_into(ifc_file, ifc_file, styles)[0]
                                messenger_wire_style.Item = elements[2].Representation.Representations[0].Items[0]

                                obj_faces = [[], [], []]
                                obj_vertices = [[], [], []]
                                # create new face and vertice groups
                                for bin_idx, bin in enumerate(face_bins):
                                    _bin_idx = np.array(bin)
                                    obj_faces[bin_idx] = faces[_bin_idx]

                                    original_index = np.unique(obj_faces[bin_idx])
                                    # extract to new shape
                                    obj_vertices[bin_idx] = np_verts[original_index]

                                    # remap to new list (without "holes")
                                    new = np.arange(0, len(original_index))
                                    obj_faces[bin_idx] = np.searchsorted(original_index, obj_faces[bin_idx], sorter=new)

                            else:
                                elements = [source_element]
                                obj_vertices = [np_verts]
                                obj_faces = [faces]

                        for idx, element in enumerate(elements):
                            # create entities
                            grouped_verts = (obj_vertices[idx]).tolist()
                            grouped_faces = (obj_faces[idx] + 1).tolist()
                            np_verts = obj_vertices[idx]

                            # triangulate everything
                            point_list = ifc_file.create_entity("IfcCartesianPointList3D", grouped_verts, [str(i) for i in range(1, np_verts.shape[0] + 1)])
                            triangulated_faceset = ifc_file.create_entity("IfcTriangulatedFaceSet",
                                                                          Coordinates=point_list, Normals=None, Closed=True,
                                                                          CoordIndex=grouped_faces, PnIndex=None)
                            shape_representation = ifc_file.create_entity("IfcShapeRepresentation",
                                                                          ContextOfItems=geo_repr_context,
                                                                          RepresentationIdentifier="Body",
                                                                          RepresentationType="Tesselation",
                                                                          Items=[triangulated_faceset])

                            # extract IfcPresentationStyle
                            try:
                                representation_item = element.Representation.Representations[0].Items[0]
                                if representation_item.is_a("IfcPolygonalFaceSet"):
                                    styles = representation_item.StyledByItem
                                    cloned_style = clone_into(ifc_file, ifc_file, styles)[0]
                                    cloned_style.Name = ifcopenshell.guid.expand(element.GlobalId)

                                else:
                                    if representation_item.is_a("IfcMappedItem"):
                                        styles = representation_item.MappingSource.MappedRepresentation.Items[0].StyledByItem[0].Styles
                                        cloned_style = clone_into(ifc_file, ifc_file, styles)[0]

                                    elif representation_item.StyledByItem:
                                        styles = representation_item.StyledByItem[0].Styles
                                        cloned_style = clone_into(ifc_file, ifc_file, styles)[0]
                                    else:
                                        raise NotImplementedError("This Representations Style is not implemented put here to do so !")

                                    for psa in cloned_style:
                                        for surface_style in psa:
                                            try:
                                                surface_style.Name = ifcopenshell.guid.expand(element.GlobalId)
                                            except Exception:
                                                raise ifcopenshell.Error("Fail to set Name of SurfaceStyle")

                                styled_item = ifc_file.create_entity("IfcStyledItem",
                                                                     Item=triangulated_faceset,
                                                                     Styles=[cloned_style],
                                                                     Name=None)
                            except Exception as e:
                                self.project.logger.warn("No representation item found for element: " + str(shape.guid))
                                raise e
                                # continue
                            element.Representation.Representations = [shape_representation]

                            # Now add elements to the correct file defined by the bounding box of the alignment
                            element_found = False
                            if len(file_containers) == 1:
                                container = file_containers[0]
                                new_element = container.ifc_file.add(element)
                                new_styled_item = container.ifc_file.add(styled_item)
                                container.class_mapping.add_entity(ifcopenshell.guid.expand(element.GlobalId), element.Name, container.path.name)
                                container.transfer_property_set(element, new_element)
                                # element_found = True
                                # bb = None
                            else:
                                for containerCount, container in enumerate(file_containers):
                                    bb = container.bounding_box
                                    if np.any((np_verts[:, 0] > bb[0][0]) & (np_verts[:, 0] < bb[1][0])):
                                        if np.any((np_verts[:, 1] > bb[0][1]) & (np_verts[:, 1] < bb[1][1])):
                                            new_element = container.ifc_file.add(element)
                                            new_styled_item = container.ifc_file.add(styled_item)
                                            container.class_mapping.add_entity(ifcopenshell.guid.expand(element.GlobalId), element.Name, container.path.name)
                                            container.transfer_property_set(element, new_element)
                                            element_found = True
                                            if ONLY_CREATE_ONE_MODEL_MULTI_TRACKS:
                                                break
                                if not element_found:
                                    not_in_any_alignment_container.ifc_file.add(element)
                                    not_in_any_alignment_container.ifc_file.add(styled_item)

                        if not iterator.next():
                            break

                # monitor if something is out of scope
                if len(not_in_any_alignment_container.ifc_file.by_type("IfcBuildingElement")) > 0:
                    file_containers.append(not_in_any_alignment_container)
                    self.project.logger.warn("Some shapes were not assigned to any alignment")

                # finalize and save containers
                for container in file_containers:
                    self.project.logger.info(f"Writing output of {container.name}")
                    container.link_products_to_site()
                    container.ifc_file.write(str(container.path.with_suffix(".ifc")))
                    container.class_mapping.save(container.path.parent / (container.path.stem + "_guid_mapping.json"))
                    global_mapping.merge(container.class_mapping)
                global_mapping.save()
            self.project.logger.info("Done extracting areas")

            # clean up
            if True:
                del bounding_box
                del cloned_style
                del element
                del element_found
                del faces
                del geo_repr_context
                del grouped_faces
                del grouped_verts
                del new_element
                del new_styled_item
                del np_verts
                del point_list
                del representation_item
                del shape_representation
                del surface_style
                del triangulated_faceset
                del verts
                del global_mapping
                del file_containers

        if "convert" in steps:
            self.project.logger.info("Converting the IFC-Files to OBJ + MTL !")
            if create_docker(self.output, self.output, "blender").returncode == 0:
                texture_path = Path(__file__).parent / "modelling" / "blender" / "textures"

                # argument displacement textures: See blender refinement for adding objects in docker processing !
                self.project.logger.info("Preparing: Textures")
                create_augmentations(texture_path / "Ground037_4K_Displacement.jpg", texture_path / "ground", 30)
                create_augmentations(texture_path / "Rocks006_4K_Displacement.jpg", texture_path / "rail-bed", 30)

                # start docker & execute conductor 1
                self.project.logger.info("Staring up docker for blender processing")
                docker_run_blender(self.output, BLENDER_VOXEL_SIZE)

                for gp in self.output.glob("*/global_position.csv"):
                    shift = np.genfromtxt(gp, delimiter=',')
                    for _csv in gp.parent.glob("*.csv"):
                        if _csv.name == "global_position.csv" or _csv.name.endswith("_local.csv"):
                            continue
                        current_alignment = Alignment.from_csv(_csv)
                        current_alignment["x"] -= shift[0]
                        current_alignment["y"] -= shift[1]
                        current_alignment["z"] -= shift[2]
                        current_alignment.to_csv(_csv.parent / f"{_csv.stem}_local.csv", index=False)
            else:
                self.project.logger.warn(f"Could not start blender docker, fallback to ifc convert instead")

                ifc_files = self.output.glob("**/*.ifc")
                from sys import platform
                if platform == "linux" or platform == "linux2":
                    url = 'https://s3.amazonaws.com/ifcopenshell-builds/IfcConvert-v0.6.0-517b819-linux64.zip'
                    convert_executable = Path(__file__).parent.absolute() / "modelling" / "IfcConvert"
                    extract = True
                elif platform == "win32":
                    url = 'https://s3.amazonaws.com/ifcopenshell-builds/IfcConvert-v0.6.0-517b819-win64.zip'
                    convert_executable = Path(__file__).parent.absolute() / "modelling" / "IfcConvert.exe"
                    extract = True
                else:
                    raise UserWarning("Get a PC !")

                # make sure IfcConvert is there
                if not convert_executable.exists():
                    self.project.logger.info(f"IFCConvert was not found at {convert_executable}")
                    import wget
                    import zipfile

                    file_name = wget.download(url, out=str(convert_executable.parent / "IfcConvert.zip"))
                    if extract:
                        with zipfile.ZipFile(convert_executable.parent / file_name, 'r') as zip_ref:
                            zip_ref.extractall(convert_executable.parent)
                        os.remove(convert_executable.parent / file_name)
                    del file_name

                if not convert_executable.exists():
                    raise FileNotFoundError("Something went wrong, please download the file manually")

                convert_executable.chmod(convert_executable.stat().st_mode | stat.S_IEXEC)
                del url

                for current_filepaths_path in ifc_files:
                    import subprocess
                    status = subprocess.run([convert_executable, current_filepaths_path, current_filepaths_path.with_suffix(".obj")])  # "--sew-shells"
                del ifc_files
                del convert_executable

        if "model_evaluation" in steps:
            self.project.logger.info("Evaluating Models")
            global_mapping = OCMapping.read(self.project.object_mapping)
            container = {_id: [] for _id in global_mapping.data["sources"].values()}

            for entity in global_mapping.data["entities"].values():
                container[entity["source_idx"]].append(entity["class_idx"])

            models_stats = {}
            for source_idx, class_idx_list in container.items():
                src = global_mapping.reverse_sources[source_idx]
                _arr = np.array(class_idx_list, dtype=int)
                # histogram = np.histogram(_arr, bins=np.unique(_arr))
                from matplotlib.pylab import plt
                _labels, _counts = np.unique(_arr, return_counts=True)
                # labels = np.arange(_labels.max()+1)
                # counts = np.zeros_like(labels)
                # counts[counts == 0] = -counts.max()
                # counts[_labels] = _counts

                plt.bar(_labels, _counts, align='center', color=(0.2, 0.4, 0.6, 0.6))
                ax = plt.gca()
                text_labels = [global_mapping.reverse_classes[i] for i in _labels]
                plt.title(src)
                plt.grid(b=True, which='major', color='gray', linestyle=':', axis="y")

                # plt.grid(b=True, which='minor', color='r', linestyle='--')
                src_ = Path(src)
                if self.show_plot:
                    ax.set_xticks(_labels, text_labels)

                    for tick in ax.get_xticklabels():
                        tick.set_rotation(45)
                    plt.show()
                else:
                    ax.set_xticks(_labels)
                    plt.tight_layout()
                    # ax.set_size_inches(10, 5)
                    plt.gcf().set_size_inches(14, 5)
                    hist_path = self.output / src_.stem / f"{src_.stem}_hist.pdf"
                    hist_path.parent.mkdir(exist_ok=True)
                    plt.savefig(hist_path, dpi=100)
                plt.clf()

                hist = {int(_labels[i]): int(_counts[i]) for i in range(len(_labels))}
                models_stats[src] = {
                    "histogram": hist,
                    "class_count": len(_labels),
                    "object_count": len(class_idx_list)
                }
            with open(self.output / f"model_statistics.json", "w") as file:
                json.dump(models_stats, file, indent=4)

        if "helios_prep" in steps:
            self.project.logger.info("Altering MTL for Helios Input")
            # load global mapping
            global_mapping = OCMapping.read(self.project.object_mapping)
            mtl_files = self.output.glob("**/*.mtl")
            for mtl in mtl_files:
                class_tmp_path = mtl.with_suffix(".class_tmp")
                guid_tmp_path = mtl.with_suffix(".guid_tmp")

                # saveguard against old files
                if mtl.with_suffix(".obj").stat().st_size < 50000:
                    continue

                # saveguard against rerunning
                if mtl.with_suffix(".original_mtl").exists():
                    shutil.move(mtl.with_suffix(".original_mtl"), mtl)

                with open(mtl, "r") as src, open(guid_tmp_path, "w") as guid_dst, open(class_tmp_path, "w") as class_dst:
                    # first_line = next(src)
                    # guid_dst.write(first_line)
                    # class_dst.write(first_line)
                    next_guid = None

                    for line in src:
                        if line.strip():
                            if line.startswith("newmtl"):
                                if next_guid:
                                    idx, class_idx, source_idx = global_mapping.data["entities"][next_guid].values()
                                    guid_dst.write(f"helios_classification {idx}\n\n")
                                    class_dst.write(f"helios_classification {class_idx}\n\n")
                                next_guid = line[7:].split("-")[-1].strip()

                            guid_dst.write(line)
                            class_dst.write(line)
                    idx, class_idx, source_idx = global_mapping.data["entities"][next_guid].values()
                    guid_dst.write(f"helios_classification {idx}\n")
                    class_dst.write(f"helios_classification {class_idx}\n")

                shutil.move(mtl, mtl.with_suffix(".original_mtl"))
                shutil.move(class_tmp_path, mtl.with_suffix(".class_mtl"))
                shutil.move(guid_tmp_path, mtl.with_suffix(".mtl"))
            self.project.logger.info("*.mtl files modified")

    @staticmethod
    def add_parser_options(subparser):
        pmo_parser = subparser.add_parser("prepare_models")
        pmo_parser.add_argument('--in', type=Path, help="IFC file or folder containing multiple ifc files",
                                dest="ifc_input_path")
        pmo_parser.add_argument('--out', type=Path, help="Output path for the obj, mtl and alignment file",
                                dest="model_output_path")
        pmo_parser.add_argument('--object_mapping', type=Path, required=False, default=None)

        pmo_parser.add_argument('--step', choices=PrepareModels._steps + ["all_steps"], help='[extract_alignment, extract_areas, convert, helios_prep]',
                                required=True, dest="secondary")

        pmo_parser.add_argument('--plot', type=bool, required=False, default=False)
        pmo_parser.add_argument('--show_plot', type=bool, required=False, default=False)
        pmo_parser.add_argument('--resolution', dest="trajectory_resolution", type=float, help="sampling space in [m]", required=False, default=1)

    def get_steps(self):
        return list(self._steps)


def docker_run_blender(input_path, voxel_size):  # , outpath=False):
    """
    StringBuilder for docker run.
    :param voxel_size:
    :param input_path:
    :return:
    """
    dstring = ["docker-compose", "exec", "-T", "-u", "mash", "blender",
               "/home/mash/blender/3.1/python/bin/python3.10", "-u", "/home/mash/scripts/blender_conductor.py",
               "--input_path", "/home/mash/data",
               "--voxel_size", str(voxel_size)]
    # if outpath:
    #     dstring += ["--output_path", "/home/phaethon/results"]

    docker_run(dstring)
