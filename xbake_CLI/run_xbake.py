import bpy
import os
import sys
import argparse

def parse_arguments():
    # Parse command-line arguments
    argv = sys.argv
    if "--" not in argv:
        return None
    argv = argv[argv.index("--") + 1:]

    parser = argparse.ArgumentParser(description="Run xbake script.")
    parser.add_argument('--lowpoly', required=True, help="Path to the lowpoly FBX file.")
    parser.add_argument('--highpoly', required=True, help="Path to the highpoly FBX file.")
    parser.add_argument('--extrusion', type=float, default=0.5, help="Extrusion value for baking.")
    parser.add_argument('--usenormal', type=bool, default=True, help="Use normal maps.")
    parser.add_argument('--normal_format', type=str, default='OPENGL', help="Normal format (OPENGL/DIRECTX).")
    parser.add_argument('--useao', type=bool, default=True, help="Use ambient occlusion.")
    parser.add_argument('--usecurvature', type=bool, default=True, help="Use curvature.")
    parser.add_argument('--useposition', type=bool, default=True, help="Use position maps.")
    parser.add_argument('--useworldspacenormal', type=bool, default=True, help="Use world-space normal maps.")
    parser.add_argument('--usemayaorientation', type=bool, default=False, help="Use Maya orientation.")
    parser.add_argument('--resolution', type=int, default=2048, help="Set Output Resolution")
    
    return parser.parse_args(argv)

def import_fbx_and_get_first_mesh(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    pre_import_objects = set(bpy.context.scene.objects)
    try:
        bpy.ops.import_scene.fbx(filepath=file_path)
        imported_objects = set(bpy.context.scene.objects) - pre_import_objects
        for obj in imported_objects:
            if obj.type == 'MESH':
                return obj
        for obj in imported_objects:
            if obj.type == 'EMPTY':
                for child in obj.children:
                    if child.type == 'MESH':
                        return child
        return None
    except Exception as e:
        print(f"Failed to import FBX: {e}")
        return None

def runbake(lowpoly, highpoly, args):
    text_block_name = "xbake_internal.py"
    if text_block_name in bpy.data.texts:
        bake_script = bpy.data.texts[text_block_name].as_string()
        #exec(bake_script)
        
        scene = bpy.context.scene
        scene.smart_bake_settings.source_object = highpoly
        scene.smart_bake_settings.target_object = lowpoly
        scene.smart_bake_settings.resolution = args.resolution
        scene.smart_bake_settings.selected_to_active
        scene.smart_bake_settings.extrusion = args.extrusion
        scene.smart_bake_settings.normal = args.usenormal
        scene.smart_bake_settings.ambient_occlusion = args.useao
        scene.smart_bake_settings.curvature = args.usecurvature
        scene.smart_bake_settings.position = args.useposition
        scene.smart_bake_settings.worldspacenormal = args.useworldspacenormal
        
        if args.usemayaorientation:
            scene.smart_bake_settings.forward_axis = 'POS_Z'
            scene.smart_bake_settings.up_axis = 'POS_Y'
        else:
            scene.smart_bake_settings.forward_axis = 'POS_Y'
            scene.smart_bake_settings.up_axis = 'POS_Z'
        
        scene.smart_bake_settings.normal_format = args.normal_format
        scene.smart_bake_settings.custom_output_path = True
        scene.smart_bake_settings.use_custom_path = True
        scene.smart_bake_settings.bake_path = os.path.dirname(args.lowpoly)
        scene.smart_bake_settings.use_object_folder = False
        
        bpy.ops.smart_bake.bake_selected_maps()
        
    else:
        print(f"Text block '{text_block_name}' not found.")

if __name__ == "__main__":
    args = parse_arguments()
    if args:
        lowpoly = import_fbx_and_get_first_mesh(args.lowpoly)
        highpoly = import_fbx_and_get_first_mesh(args.highpoly)
        if lowpoly and highpoly:
            runbake(lowpoly, highpoly, args)
        if lowpoly:
            bpy.data.objects.remove(lowpoly, do_unlink=True)
        if highpoly:
            bpy.data.objects.remove(highpoly, do_unlink=True)
        
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        bpy.ops.wm.quit_blender()
    else:
        print("Error: Failed to load lowpoly or highpoly meshes.")
