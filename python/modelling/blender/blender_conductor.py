#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de       
# ----------------------------------------------------------------------------------------------------------------------------------

import argparse
import subprocess
from pathlib import Path
import sys

blender_executable = "/home/mash/blender/blender"
script_path = "/home/mash/scripts/blender_refinement.py"

if __name__ == '__main__':
    # ~/blender/3.1/python/bin
    parser = argparse.ArgumentParser(description='Launch inside Docker')
    parser.add_argument('--input_path', type=Path, help="Path to files", required=True)
    parser.add_argument('--output_path', type=Path, help="OutputPath", default=None)
    parser.add_argument('--voxel_size', type=float, help="Grid size for the displacement", default=0.05)

    from_main_script = parser.parse_args()
    from_main_script.input_path = from_main_script.input_path.expanduser()
    if from_main_script.output_path:
        from_main_script.output_path = from_main_script.output_path.expanduser()

    print("Blender Operations Commencing")
    ifc_files = from_main_script.input_path.glob("**/*.ifc")
    for ifc_path in ifc_files:
        print(f"Processing: {ifc_path.name}")
        obj_path = ifc_path.with_suffix(".obj")
        status = subprocess.run([blender_executable, "--background", "--python", script_path,
                                 "-input_path", ifc_path,
                                 "-output_path", obj_path,
                                 "-voxel_size", str(from_main_script.voxel_size)])


