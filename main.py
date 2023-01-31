#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import argparse
from pathlib import Path
from python.t1_prepare_models import PrepareModels
from python.t2_simulate import Simulate
from python.t3_prepare_labels import PrepareLabels
from python.t4_evaluation import Evaluate
from python.t5_visualize import Visualize
from collections import OrderedDict
from python.common.project import Project, to_pascal_case
import sys

_allowed_tasks = OrderedDict([
    ("prepare_models", PrepareModels),
    ("simulate", Simulate),
    ("prepare_labels", PrepareLabels),
    ("evaluate", Evaluate),
    ("visualize", Visualize)
])

if __name__ == "__main__":
    print("\nParameters:")
    print(' '.join(sys.argv[1:]))

    parser = argparse.ArgumentParser(description='Launcher for 3D Point RailTwin preparation')
    subparser = parser.add_subparsers(help="Where does this go?", dest="primary")
    subparser.required = True

    # Parse if the whole project is ran
    all_parser = subparser.add_parser("pre-production")
    all_parser.add_argument('--in', type=Path, help="IFC file or folder containing multiple ifc files", dest="all_in")
    all_parser.add_argument('--out', type=Path, help="Output path for the results", dest="all_out")
    all_parser.add_argument('--object_mapping', type=Path, required=False, default=None)
    all_parser.add_argument('--label_partition', type=int, required=False, default=None)
    all_parser.add_argument('--trajectory_resolution', type=float, required=False, default=None)
    all_parser.add_argument("--sysco_map", type=Path, required=False, dest="system_component_mapping_path",
                            default=Path(__file__).parent / "python" / "labeling" / "rtsysco_mapping.json")
    # all_parser.add_argument('--classes', type=Path, required=False, default="class_database.json")
    # all_parser.add_argument('--grouping', type=Path, required=False, default="group_database.json", dest="group_obj")

    # Add the steps' parser as subparsers
    PrepareModels.add_parser_options(subparser)
    Simulate.add_parser_options(subparser)
    PrepareLabels.add_parser_options(subparser)
    Evaluate.add_parser_options(subparser)
    # Infer.add_parser_options(subparser)
    Visualize.add_parser_options(subparser)

    args = parser.parse_args()

    # Some fixes (should not be here I guess ?)
    if args.primary == "prepare_labels":
        try:
            if args.secondary == "kpconv":
                raise AttributeError("This is good ! Hidden goto :)")
        except AttributeError:
            if args.classes is None:
                parser.error("The full prepare_label as well as the step kpconv require --classes to point to a valid file")

    project_conf = Project(args)

    if args.primary == "pre-production":
        # List primary tasks
        selected_tasks = ["prepare_models", "simulate"]

        # chain tasks
        project_conf.step = "all_steps"

        project_conf.ifc_input_path = args.all_in
        project_conf.model_output_path = args.all_out
        project_conf.trajectory_resolution = 1 if args.trajectory_resolution is None else args.trajectory_resolution
        project_conf.plot = True
        project_conf.show_plot = False

        project_conf.simulation_input = args.all_out
        project_conf.simulation_output = None

        project_conf.label_input_path = args.all_out
        project_conf.batch_size = PrepareLabels._default_batchsize
        project_conf.partition = 1 if args.label_partition is None else args.label_partition
        project_conf.recursive = True
        project_conf.label_output_path = None

    else:
        selected_tasks = [args.primary]

    for task in selected_tasks:
        task_executor = getattr(sys.modules[__name__], to_pascal_case(task))(project_conf)
        task_executor.run()
