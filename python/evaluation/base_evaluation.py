# 14.06.22----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler 
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------

import json
from pathlib import Path

import pandas
import numpy as np
from sklearn.neighbors import KDTree

from python.common.shared.common.logger import RailTwinLogger

logger = RailTwinLogger.create()


class BaseEvaluation:

    def __init__(self):
        pass

    def eval(self, pc: pandas.DataFrame):
        statistics = {
            # basic
            "point_count": 0,
            "covered_area": 0.0,
            "ratio3D": [0.0, 0.0, 0.0],
            "covered_volume": 0.0,
            # nn-th
            "min_dist": 0,
            "avg_min_dist": 0,
            "nn5_avg": 0.0,
        }
        if hasattr(pc, "x") and hasattr(pc, "y") and hasattr(pc, "z"):
            statistics["point_count"] = len(pc)
            max = pc.max()
            min = pc.min()
            spans = max - min
            statistics["covered_area"] = spans.x * spans.y
            statistics["covered_volume"] = spans.x * spans.y * spans.z
            statistics["ratio3D"] = [spans.x / spans.z, spans.y / spans.z, 1]

            for column in pc:
                statistics[f"{column}_min"] = min[column]
                statistics[f"{column}_max"] = max[column]
                statistics[f"{column}_span"] = spans[column]

            numpy_points = pc[["x", "y", "z"]].to_numpy()
            kdt = KDTree(numpy_points, leaf_size=30, metric='euclidean')
            chunks = len(pc) / 10000

            collector = []
            for chunk in np.array_split(numpy_points, chunks):
                dist, ind = kdt.query(chunk, k=5, return_distance=True)
                collector.append([dist[:, 1].min(), dist[:, 1].mean(), dist[:, 1:].mean()])

            collector = np.array(collector)
            statistics["min_dist"] = collector[:, 0].min()
            statistics["avg_min_dist"] = collector[:, 1].mean()
            statistics["nn5_avg"] = collector[:, 2].mean()

            if hasattr(pc, "intensity"):
                statistics["min_intensity"] = pc.intensity.min()
                statistics["max_intensity"] = pc.intensity.max()

        return statistics

    def save(self, path: Path):
        pass

    def plot(self, path: Path):
        pass


class ClassEvaluation:
    def __init__(self, mapping_path="", sysco_path=""):
        self.mapping = None
        self.inverse_mapping = None
        self.sysco_mapping = None

        if mapping_path:
            with open(mapping_path, "r") as f:
                self.mapping = json.load(f)
            self.inverse_mapping = {k: i for i, k in self.mapping["classes"].items()}

        if sysco_path:
            with open(sysco_path, "r") as f:
                self.sysco_mapping = json.load(f)

    def eval(self, pc: pandas.DataFrame):
        statistics = {
            "class_count": 0,
            "class_histogram": {},
            "system_histogram": {},
            "system_pointogram": {},
            "class_pointogram": {}
        }
        if hasattr(pc, "class") and hasattr(pc, "object_id") and self.mapping:
            object_points = pc["object_id"].value_counts()

            collector = {}
            for object_id, points in object_points.items():
                first_row = pc[pc["object_id"] == object_id].iloc[0]
                class_name = self.inverse_mapping[first_row["class"]]
                if class_name not in collector:
                    collector[class_name] = {"points": 0, "object_count": 0}
                collector[class_name]["points"] += points
                collector[class_name]["object_count"] += 1

            statistics["class_count"] = len(collector)
            for key, dat in collector.items():
                statistics["class_histogram"][key] = dat["object_count"]
                statistics["class_pointogram"][key] = dat["points"]

            sysco_collector = {}
            if self.sysco_mapping:
                for key, dat in collector.items():
                    if key in self.sysco_mapping["systems"]:
                        new_key = self.sysco_mapping["systems"][key]
                        if new_key not in sysco_collector:
                            sysco_collector[new_key] = {"points": 0, "object_count": 0}
                        sysco_collector[new_key]["points"] = dat["points"]
                        sysco_collector[new_key]["object_count"] = dat["object_count"]

                    else:
                        logger.warn(f"{key} not in given sysco_mapping")

                for key, dat in sysco_collector.items():
                    statistics["system_histogram"][key] = dat["object_count"]
                    statistics["system_pointogram"][key] = dat["points"]

        return statistics

    def save(self, path: Path):
        pass

    def plot(self, path: Path):
        pass
