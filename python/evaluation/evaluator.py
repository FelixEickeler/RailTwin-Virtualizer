# 14.06.22----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler 
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------
#
#
import json
from pathlib import Path

import numpy as np
import pandas

from python.common.shared.common.io import read
from python.evaluation.base_evaluation import BaseEvaluation
from python.evaluation.cseg_evaluation import CloudSegmentationEvaluation, matplotlib_confusion_matrix, get_overview
from functools import partial


class EvaluatorResult:
    def __init__(self):
        self.files = []
        self.data = {}

    def append(self, name: str):
        self.files.append(name)
        self.data[name] = {"name": name}
        return partial(self.update, name)

    def update(self, name, data):
        self.data[name].update(data)

    def agglo(self):
        pass

    def frame(self):
        return pandas.DataFrame([self.data[name] for name in sorted(self.files)])


class Evaluator:

    def __init__(self):
        self.evaluations = []
        self.results = EvaluatorResult()

    def eval(self, path):
        data = read(path)
        dat = {}
        try:
            with open(path.parent / "metadata.json") as f:
                dat = json.load(f)
            data.metadata = dat
        except:
            data.metadata = {}

        for es in self.evaluations:
            collector = self.results.append(path)
            collector(es.eval(data))

    def agglomerate(self):
        pass
        # for es in self.evaluations:
        #     collector = self.results.append(es)
        #     collector(es.eval(data))

    def save(self, path: Path):
        df = self.results.frame()
        pandas.options.display.max_colwidth = 220
        df.to_csv(path, index=True)

    def confusion(self):
        collector = []
        labels = None
        for r in self.results.data.values():
            if "confusion_matrix" in r:
                collector.append(r["confusion_matrix"])
                if not labels:
                    labels = r["labels"]
        if collector:
            sum_conf = np.zeros_like(collector[0])
            try:
                for c in collector:
                    sum_conf += c
                # sum_conf / len(collector)
            except:
                print("weird confusion matrices")

            # Some overview functions

            # matplotlib_confusion_matrix(sum_conf.to_numpy()[1:,1:], labels[1:])
            import matplotlib.pyplot as plt
            # plt.savefig("<path>/figures/11classes_synth_cm.pdf")
            # plt.clf()
            # get_overview(sum_conf.to_numpy()[1:,1:], labels[1:])
            # plt.savefig("<path>/figures/16classes_synth_cm_overview.pdf")
