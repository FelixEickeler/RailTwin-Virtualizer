#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

from pathlib import Path
from python.evaluation.base_evaluation import BaseEvaluation, ClassEvaluation
from python.evaluation.cseg_evaluation import CloudSegmentationEvaluation
from python.evaluation.evaluator import Evaluator


class Evaluate:
    _steps = ["base_evaluation", "cloud_segmentation", "class_evaluation"]

    def __init__(self, _project):
        self.project = _project
        self.input_path = self.project.input_path

    def run(self):
        logger = self.project.logger
        steps = [self.project.step]

        evaluator = Evaluator()
        if "base_evaluation" in steps:  evaluator.evaluations += [BaseEvaluation()]
        if "class_evaluation" in steps:
            sysco_path = self.project.sysco_mapping
            mapping_path = self.project.mapping_path
            evaluator.evaluations += [ClassEvaluation(mapping_path=mapping_path, sysco_path=sysco_path)]
        if "cloud_segmentation" in steps: evaluator.evaluations += [CloudSegmentationEvaluation()]

        if evaluator.evaluations:

            inputs = [self.input_path]
            inputs += [p for p in self.input_path.iterdir() if p.is_dir()]

            for i, path in enumerate(inputs):
                plys = list(path.glob("*.ply"))
                for ply_path in plys:
                    logger.info(f"Evaluating the cloud segmentation of: {ply_path}")
                    evaluator.eval(ply_path)
                # evaluator.save(path / "evaluation.csv")
                # print("dododod")

        if "base_evaluation" in steps:
            res = evaluator.results.data

        if "class_evaluation" in steps:
            # latex table print
            collector = {}
            for key, dat in evaluator.results.data.items():
                for sys, count in dat["system_histogram"].items():
                    if sys not in collector:
                        collector[sys] = {}
                    collector[sys][key.stem] = count

            for key, dat in collector.items():
                val = [str(v) for v in dat.values()]
                print(f"{key} & {' & '.join(val)} \\\\")

        if "cloud_segmentation" in steps:
            evaluator.confusion()

        if "test" in steps:
            pass  # some test and graphs maybe ?

        if "infer" in steps:
            pass  # inference stuff here ?

    @staticmethod
    def add_parser_options(subparser):
        pmo_parser = subparser.add_parser("evaluate")
        pmo_parser.add_argument('--in', type=Path, dest="input_path", help="Output path for the evaluate stuff")
        pmo_parser.add_argument('--step', choices=Evaluate._steps, help=f'[{",".join(Evaluate._steps)}]',
                                required=False, dest="secondary")
        pmo_parser.add_argument('--mapping', required=False, dest="mapping_path")
        pmo_parser.add_argument('--sysco', required=False, dest="sysco_mapping")
