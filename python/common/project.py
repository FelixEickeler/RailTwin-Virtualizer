#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import json
from pathlib import Path
import spdlog as spd
from json import JSONEncoder
import re
import ast

_str2dict_pattern = re.compile(r'"?(\w*)"?:"?(\d*)"?,?')


def str2dict(_str: str):
    groups = _str2dict_pattern.findall(_str)
    res = {}
    for match in groups:
        try:
            try:
                res[match[0]] = int(match[1])
            except Exception as e:
                res[match[0]] = float(match[1])
                raise e
        except:
            res[match[0]] = match[1]
    return res


def to_pascal_case(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return ''.join(x.title() for x in components)


def to_snake_case(CamelCase):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', CamelCase).lower()


def convKey2Int(dict):
    return {int(k): v for k, v in dict.items()}


class DictEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, "__dict__"):
            ret = o.__dict__
        else:
            ret = str(o)
        return ret


class ClassCollection:

    def __init__(self, json_path, collection_dict):
        self.path = Path(json_path)
        self.data = collection_dict

    def __iter__(self):
        return self.data

    def __next__(self):
        yield next(self.data)

    def save(self):
        output = json.dumps(self, cls=DictEncoder, indent=4, sort_keys=True)
        with open(self.path, "w") as f:
            f.write(output)

    @staticmethod
    def from_json(json_object_or_path):
        if isinstance(json_object_or_path, Path):
            with open(json_object_or_path) as f:
                data = json.load(f)
        else:
            data = json.loads(json_object_or_path)

        if ("data" and "path") in data:
            return ClassCollection(Path(data["path"]), convKey2Int(data['data']))


class ObjectGroups:
    def __init__(self, _key_map: dict, _obj_map: dict, in_memory: bool = False):
        self.key_map = _key_map
        self.obj_map = _obj_map
        self.in_memory = in_memory

    def groups(self):
        inv_map = {}
        for k, v in self.key_map.items():
            inv_map[v] = inv_map.get(v, []) + [k]
        return inv_map

    def group_ids(self, key, value):
        if key in self.key_map:
            new_key = self.key_map[key]
            new_value = self.obj_map[new_key]
        else:
            new_key = key
            new_value = value
        return new_key, new_value

    def save(self, path):
        output = json.dumps(self, cls=DictEncoder, indent=4, sort_keys=True)
        with open(path, "w") as f:
            f.write(output)

    @staticmethod
    def from_json(json_object_or_path):
        if isinstance(json_object_or_path, Path):
            with open(json_object_or_path) as f:
                data = json.load(f)
        else:
            data = json.loads(json_object_or_path)

        if ("key_map" and "obj_map") in data:
            return ObjectGroups(convKey2Int(data['key_map']), convKey2Int(data['obj_map']))


class Project:
    def __init__(self, args):
        self.logger = spd.ConsoleLogger("RailtTwin", False, True, True)
        self.logger.set_level(spd.LogLevel.INFO)

        for key, value in args.__dict__.items():
            self.__dict__[key] = value

        if hasattr(args, "project_path"):
            self.base_path = args.project_path.expanduser()

        if hasattr(args, "classes"):
            if args.classes is None:
                collection = None
                raise AssertionError("class required but not given?")
            elif args.classes == "class_database.json":
                class_collection_path = self.base_path / args.classes
                collection = ClassCollection(class_collection_path, {})
            else:
                class_collection_path = args.classes.expanduser()
                if not class_collection_path.exists():
                    raise FileNotFoundError("Class file does not exist !")
                collection = ClassCollection.from_json(class_collection_path)
        else:
            collection = None
        self.class_collection = collection

        # if hasattr(args, "grouping"):
        #     if args.grouping is None:
        #         grouping = None
        #     elif args.grouping is "grouping_database.json":
        #         grouping_collection_path = self.base_path / args.grouping
        #         grouping = ObjectGroups(grouping_collection_path, {})
        #     else:
        #         grouping_collection_path = args.grouping.expanduser()
        #         if not grouping_collection_path.exists():
        #             raise FileNotFoundError("Class file does not exist !")
        #         grouping = ObjectGroups.from_json(grouping_collection_path)
        # else:
        #     grouping = None
        # self.obj_groups = ObjectGroups({},{}, in_memory=True)

        if hasattr(args, "in"):
            self.input_path = args.__dict__["in"].expanduser()
            self.output_path = args.out.expanduser()

        if hasattr(args, "out"):
            self.output_path = args.out.expanduser()

        if hasattr(args, "secondary"):
            self.step = args.secondary
        else:
            self.step = "all_steps"

        # if hasattr(args, "parition"):
        #     self.partition =
