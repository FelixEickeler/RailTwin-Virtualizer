#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from ..common.shared.common.logger import RailTwinLogger

logger = RailTwinLogger.create()

class OCMapping:

    def __init__(self):
        self.data = {
            "metadata": {
                "guid": str(uuid4()),
                "number_of_classes": 0,
                "number_of_objects": 0,
                "number_of_entities": 0,
                "last_update": datetime.now().strftime("%Y-%m-%d, %H:%M:%S"),
                "distribution": {},
            },
            "sources": {},
            "classes": {},
            "entities": {}
        }
        self.path = Path("")
        self.reverse_sources = {}
        self.reverse_classes = {}
        self.idx2class = {}

    def add_entity(self, guid: str, nclass: str, src: str):
        debug = False
        if guid not in self.data["entities"]:
            debug = True
            local_id = len(self.data["entities"])
            class_idx = self.add_class(nclass)
            source_idx = self.add_source(src)

            self.data["entities"][guid] = {
                "idx": local_id,
                "class_idx": class_idx,
                "source_idx": source_idx
            }
            self.data["metadata"]["number_of_entities"] += 1
            self.data["metadata"]["distribution"][nclass] += 1
            self.idx2class[local_id] = self.data["entities"][guid]

        else:
            local_id = self.data["entities"][guid]["idx"]
        # print(f"{nclass} \t -- \t {guid} \t\t was_new : {'yes' if debug else 'no'}")
        return local_id

    def add_source(self, src):
        if src not in self.data["sources"]:
            this_src_idx = len(self.data["sources"])
            self.data["sources"][src] = this_src_idx
            self.reverse_sources[this_src_idx] = src
            self.data["metadata"]["number_of_objects"] += 1
        return self.data["sources"][src]

    def add_class(self, nclass):
        if nclass not in self.data["classes"]:
            this_nclass_idx = len(self.data["classes"])
            self.data["classes"][nclass] = this_nclass_idx
            self.reverse_classes[this_nclass_idx] = nclass
            self.data["metadata"]["number_of_classes"] += 1
            self.data["metadata"]["distribution"][nclass] = 0
        return self.data["classes"][nclass]

    @classmethod
    def read(cls, path):
        mapping = OCMapping()
        if not path.exists():
            logger.warn(f"No object mapping was found at the given path! A new mapping will be created at {path}")
        else:
            with open(path) as mapping_file:
                mapping.data = json.load(mapping_file)
            if logger:
                logger.info(f"Mapping was found and {mapping.data['metadata']['number_of_entities']} entites were loaded")
        mapping.path = path
        mapping.reverse_sources = {value: key for key, value in mapping.data["sources"].items()}
        mapping.reverse_classes = {value: key for key, value in mapping.data["classes"].items()}
        mapping.idx2class = {value["idx"]: value for key, value in mapping.data["entities"].items()}
        return mapping

    def save(self, path=None):
        if path is None:
            path = self.path
        path.parent.mkdir(exist_ok=True, parents=True)
        with open(path, 'w', encoding='utf-8') as f:
            self.data["metadata"]["last_update"] = datetime.now().strftime("%Y-%m-%d, %H:%M:%S")
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def merge(self, mapping):
        for guid, entity in mapping.data["entities"].items():
            entity_class = mapping.reverse_classes[entity["class_idx"]]
            entity_source = mapping.reverse_sources[entity["source_idx"]]
            this_id = self.add_entity(guid, entity_class, entity_source)
        return self