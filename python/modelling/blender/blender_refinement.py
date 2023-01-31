# 09.05.22----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de
# ----------------------------------------------------------------------------------------------------------------
#
#
import math
import random
from pathlib import Path
import bpy
import sys
import logging
import blenderbim.bim.import_ifc

sys.path.append(str(Path(__file__).parent))
print(Path(__file__).parent)
import argparse_for_blender as argparse
# import argparse
# from argparse_for_blender import ArgumentParserForBlender


def load_textures(folder):
    logging.info(f"Texture folder: {folder}")
    texture_path = folder.glob("*.jpg")
    collector = []
    for path in texture_path:
        texture = bpy.data.textures.new(path.stem, type='IMAGE')
        bpy.data.images.load(str(path), check_existing=True)
        texture.image = bpy.data.images[path.name]
        collector.append(texture)
    return collector


def refine(objects, voxel_size):
    for name, path in objects.items():
        textures = load_textures(path)
        sel_objects = [objName for objName in bpy.data.objects.keys() if objName.find(name) != -1]
        if len(sel_objects) == 0:
            continue
        repeat = math.ceil(len(sel_objects) / len(textures))
        augmented_textures = random.sample(textures * repeat, len(sel_objects))

        for i, objName in enumerate(sel_objects):
            print(f"\tRefining: {objName}")

            # remesh
            obj = bpy.data.objects[objName]
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            # bpy.context.view_layer.objects.active = bpy.data.objects[key]
            obj.modifiers.new(name="remesh", type="REMESH")
            obj.modifiers["remesh"].voxel_size = voxel_size
            bpy.ops.object.modifier_apply(modifier="remesh")

            # add & apply displacement
            obj.modifiers.new(name="displace", type="DISPLACE")
            obj.modifiers["displace"].mid_level = 0.87 + random.random() / 8
            obj.modifiers["displace"].strength = 0.15 + random.random() / 16
            obj.modifiers["displace"].texture = augmented_textures[i]
            bpy.ops.object.modifier_apply(modifier="displace")


if __name__ == "__main__":
    # parser = arparse.ArgumentParserForBlender(description='Launch as Docker')
    parser = argparse.ArgumentParserForBlender(description='Launch from Docker')
    parser.add_argument('-input_path', type=Path, help="Path to files")
    parser.add_argument('-output_path', type=Path, help="OutputPath")
    parser.add_argument('-voxel_size', type=float, help="Grid size for the displacement", default=0.05)
    from_conductor, unknown = parser.parse_known_args()
    print(f"I parsed: {from_conductor}")
    # remove cube
    bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)

    # import ifc file
    print(sys.argv)
    sys.argv = []
    print(f"Opening ifc file: {from_conductor.input_path}")
    # bpy.ops.import_ifc.bim(filepath=str())
    ifc_import_settings = blenderbim.bim.import_ifc.IfcImportSettings.factory(bpy.context, str(from_conductor.input_path), logging.getLogger('ImportIFC'))
    ifc_importer = blenderbim.bim.import_ifc.IfcImporter(ifc_import_settings)
    ifc_importer.execute()

    with open(from_conductor.input_path.parent / "global_position.csv","w") as out:
        props = bpy.context.scene.BIMGeoreferenceProperties
        x = props.blender_eastings
        y = props.blender_northings
        z = props.blender_orthogonal_height
        out.write(f"{x},{y},{z}")

    # create displacement mesh
    displace = {
        "Bettung": Path("/home/mash/scripts/textures/rail-bed"),
        "Frostschutz": Path("/home/mash/scripts/textures/ground"),
    }
    refine(displace, from_conductor.voxel_size)


    # export obj
    bpy.ops.export_scene.obj(filepath=str(from_conductor.output_path), check_existing=False,
                             axis_forward='Y', axis_up='Z',
                             use_normals=False, use_uvs=False, use_materials=True,
                             use_triangles=True, use_nurbs=False, use_vertex_groups=False,
                             use_blen_objects=True, group_by_object=False, group_by_material=False, keep_vertex_order=False, global_scale=1, path_mode='AUTO')
    logging.info(f"Export of {str(from_conductor.output_path)} complete")
    bpy.ops.wm.quit_blender()

# if __name__ == "__main__":
#    refine()


# # create UV mapping
# obj.select_set(True)
# bpy.ops.object.mode_set(mode="EDIT")
# bpy.ops.mesh.select_all(action="SELECT")
# bpy.ops.uv.smart_project(angle_limit=66)  # , island_margin=0.02)
# bpy.ops.object.mode_set(mode='OBJECT')
#
# # randomize UVMap
# uvMapName = 'UVMap'
# pivot = Vector((0.5, 0.5))
# scale = Vector((4, 4))
# uvMap = obj.data.uv_layers[uvMapName]
# ScaleUV(uvMap, scale, pivot)
# bpy.ops.mesh.select_all(action='DESELECT')

# from mathutils import Vector


# # Scale a 2D vector v, considering a scale s and a pivot point p
# def Scale2D(v, s, p, v0):
#     return p[0] + s[0] * (v[0] - p[0]) + v0[0], p[1] + s[1] * (v[1] - p[1]) + v0[1]
#
#
# # Scale a UV map iterating over its coordinates to a given scale and with a pivot point
# def ScaleUV(uvMap, scale, pivot, shift=(0, 0)):
#     for uvIndex in range(len(uvMap.data)):
#         uvMap.data[uvIndex].uv = Scale2D(uvMap.data[uvIndex].uv, scale, pivot, shift)
