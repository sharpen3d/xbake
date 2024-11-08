"""
Title: xBake
Description: The intuitive, all-in-one solution for simplified and powerful texture baking
Author: Luke Stilson
Date: 2024-11-07
Version: 1.0.0

Thanks for getting baked with me.
~ https://lukestilson.com ~
"""

import bpy
import os
import mathutils
import re
import subprocess

def normalize_to_unit_cube(obj):
    # Store original location and scale
    original_data[obj.name] = {
        "location": obj.location.copy(),
        "scale": obj.scale.copy(),
    }

    # Calculate the object's bounding box in world space
    bbox_world = [obj.matrix_world @ mathutils.Vector(corner) for corner in obj.bound_box]
    bbox_min = mathutils.Vector([min(v[i] for v in bbox_world) for i in range(3)])
    bbox_max = mathutils.Vector([max(v[i] for v in bbox_world) for i in range(3)])
    bbox_size = bbox_max - bbox_min

    # Calculate the scale factors to fit the 0-1 range
    scale_factors = mathutils.Vector([1.0 / max(bbox_size[i], 1e-6) for i in range(3)])

    # Apply scale and position adjustment directly
    obj.scale = mathutils.Vector([obj.scale[i] * scale_factors[i] for i in range(3)])
    obj.location -= (bbox_min * scale_factors)

    print(f"{obj.name} normalized to unit cube")

def revert_normalization(obj):
    if obj.name not in original_data:
        print(f"No original data stored for {obj.name}")
        return
    
    # Retrieve and apply original location and scale
    obj.location = original_data[obj.name]["location"]
    obj.scale = original_data[obj.name]["scale"]

    # Clean up stored data
    del original_data[obj.name]

    print(f"{obj.name} reverted to original transformation")
    
# Utility UI toggles 
def update_automatic_output(self, context):
    """Ensure only automatic output is active if selected."""
    if self.automatic_output_path:
        self.custom_output_path = False
    else:
        self.custom_output_path = True

def update_custom_output(self, context):
    """Ensure only custom output is active if selected."""
    if self.custom_output_path:
        self.automatic_output_path = False
    else:
        self.automatic_output_path = True
#        self.use_custom_name = False

def update_selected_to_active(self, context):
    if self.selected_to_active:
        self.single_object = False
    else:
        self.single_object = True

def update_single_object(self, context):
    if self.single_object:
        self.selected_to_active = False
    else:
        self.selected_to_active = True
        
def update_naming_uppercase(self, context):
    if self.naming_uppercase:
        self.naming_lowercase = False
        self.naming_pascalcase = False

def update_naming_lowercase(self, context):
    if self.naming_lowercase:
        self.naming_uppercase = False
        self.naming_pascalcase = False

def update_naming_pascalcase(self, context):
    if self.naming_pascalcase:
        self.naming_uppercase = False
        self.naming_lowercase = False

def update_bake_margin(self, context):
    # Access properties from the PropertyGroup instance (self)
    resolution = self.resolution
    margin_percentage = self.margin_percentage / 100  # Convert to a fraction

    # Update the bake margin in pixels
    context.scene.render.bake.margin = int(resolution * margin_percentage)
                 
class BakeSettings(bpy.types.PropertyGroup):
    #coordinate system
    forward_axis: bpy.props.EnumProperty(
        name="Forward Axis",
        items=[
            ('POS_Y', '+Y', 'Positive Y Axis (Default)'),
            ('NEG_Y', '-Y', 'Negative Y Axis'),
            ('POS_X', '+X', 'Positive X Axis'),
            ('NEG_X', '-X', 'Negative X Axis'),
            ('POS_Z', '+Z', 'Positive Z Axis'),
            ('NEG_Z', '-Z', 'Negative Z Axis')
        ],
        default='POS_Y'
    )

    up_axis: bpy.props.EnumProperty(
        name="Up Axis",
        items=[
            ('POS_Y', '+Y', 'Positive Y Axis'),
            ('NEG_Y', '-Y', 'Negative Y Axis'),
            ('POS_X', '+X', 'Positive X Axis'),
            ('NEG_X', '-X', 'Negative X Axis'),
            ('POS_Z', '+Z', 'Positive Z Axis (Default)'),
            ('NEG_Z', '-Z', 'Negative Z Axis')
        ],
        default='POS_Z'
    )
    
    normal_format: bpy.props.EnumProperty(
        name="Normal Format",
        items=[
            ('OPENGL', 'OpenGL', 'OpenGL Normals (Default)'),
            ('DIRECTX', 'DirectX', 'DirectX Normals')
        ],
        default='OPENGL'
    )
    
    margin_percentage: bpy.props.FloatProperty(
        name="Bake Margin (%)",
        description="Set the bake margin as a percentage of resolution",
        min=0, max=100,
        default=10.0,
        subtype='PERCENTAGE',
        update=update_bake_margin  # Assign the update function here
    )
    
    # Resolution setting
    resolution: bpy.props.IntProperty(name="Resolution", default=1024, min=64, max=4096, update=update_bake_margin)
    
    # Contribution settings
    direct: bpy.props.BoolProperty(name="Direct Lighting", default=True)
    indirect: bpy.props.BoolProperty(name="Indirect Lighting", default=True)
    color: bpy.props.BoolProperty(name="Color Contribution", default=True)

    selected_to_active: bpy.props.BoolProperty(
        name="Selected to Active",
        default=True,
        update=update_selected_to_active
    )
    single_object: bpy.props.BoolProperty(
        name="Single Object",
        default=False,
        update=update_single_object
    )
    
    cage: bpy.props.BoolProperty(name="Use Cage", default=False)
    extrusion: bpy.props.FloatProperty(name="Extrusion", default=0.5, min=0.0, max=1.0)
    max_ray_distance: bpy.props.FloatProperty(name="Max Ray Distance", default=0.0, min=0.0, max=10.0)
    
    # Object properies
    cage_object: bpy.props.PointerProperty(
        name="Cage Object",
        type=bpy.types.Object,
        description="Select an object to use as the cage"
    )
    
    source_object: bpy.props.PointerProperty(
        name="Source Object",
        type=bpy.types.Object,
        description="Object to bake from (typically high-poly)"
    )
    
    target_object: bpy.props.PointerProperty(
        name="Source Object",
        type=bpy.types.Object,
        description="Object to bake to (typically low-poly)"
    )
    
    # Map types (Grouped under standard and additional categories)
    standard_maps: bpy.props.BoolProperty(name="Standard Maps Expanded", default=False)
    additional_maps: bpy.props.BoolProperty(name="Additional Maps Expanded", default=False)
    
    naming_uppercase: bpy.props.BoolProperty(name="Uppercase", default=False, update=update_naming_uppercase)
    naming_lowercase: bpy.props.BoolProperty(name="Lowercase", default=True, update=update_naming_lowercase)
    naming_pascalcase: bpy.props.BoolProperty(name="Pascal", default=False, update=update_naming_pascalcase)
    naming_separator: bpy.props.StringProperty(name="separator", default="_")
    mapname_separator: bpy.props.StringProperty(name="separator", default="_")
    
    # Standard map settings
    normal: bpy.props.BoolProperty(name="Normal")
    curvature: bpy.props.BoolProperty(name="Curvature")
    worldspacenormal: bpy.props.BoolProperty(name="World Space Normal")
    position: bpy.props.BoolProperty(name="Position")
    ambient_occlusion: bpy.props.BoolProperty(name="Ambient Occlusion")
    curvaturecontrast: bpy.props.FloatProperty(name="Curvature Contrast", default=0.5, min=0.0, max=1.0)

    # Additional map settings
    combined: bpy.props.BoolProperty(name="Combined")
    shadow: bpy.props.BoolProperty(name="Shadow")
    uv: bpy.props.BoolProperty(name="UV")
    roughness: bpy.props.BoolProperty(name="Roughness")
    emit: bpy.props.BoolProperty(name="Emit")
    environment: bpy.props.BoolProperty(name="Environment")
    diffuse: bpy.props.BoolProperty(name="Diffuse")
    glossy: bpy.props.BoolProperty(name="Glossy")
    transmission: bpy.props.BoolProperty(name="Transmission")
    
    use_custom_name: bpy.props.BoolProperty(name="Use Custom Name", default = False)
    use_custom_path: bpy.props.BoolProperty(name="Use Custom Path", default = False)
    custom_name: bpy.props.StringProperty(name="Custom Name", default = "custom_name")
    use_object_folder: bpy.props.BoolProperty(name="Use Object Folder", default = True)
    use_subfolder: bpy.props.BoolProperty(name="Use Sub-Folder", default = True)
    subfolder_name: bpy.props.StringProperty(name="Sub-Folder", default = "baked_maps")
    
    UVOpacity: bpy.props.FloatProperty(name="UV Opacity", default = 1.0, min=0.0, max=1.0)
    show_hierarchy: bpy.props.BoolProperty(name="Output Hierarchy", default=False)
    bake_button: bpy.props.BoolProperty(name="Bake Button", description="Bake Selected Maps", default=True)
    should_bake: bpy.props.BoolProperty(name="Should Bake", default=False)  # Flag for baking action
    
    expand_cola: bpy.props.BoolProperty(name="Expand Cola", default=True)
    expand_colb: bpy.props.BoolProperty(name="Expand Colb", default=True)
    
    # Toggle properties for automatic or custom output path
    automatic_output_path: bpy.props.BoolProperty(
        name="Automatic Output Path",
        default=True,
        update=update_automatic_output
    )
    custom_output_path: bpy.props.BoolProperty(
        name="Custom Output Path",
        default=False,
        update=update_custom_output
    )
    
    bake_path: bpy.props.StringProperty(
        name="Bake Output Path",
        description="Select a directory",
        subtype='DIR_PATH'
    )
    
    margin_type: bpy.props.EnumProperty(
        name="Margin Type",
        description="Choose margin type for baking",
        items=[
            ('EXTEND', "Extend", "Extend colors from the edges"),
            ('ADJACENT_FACES', "Adjacent Faces", "Blend colors based on adjacent faces")
        ],
        default='EXTEND'
    )

        
            
class SmartBakingPanel(bpy.types.Panel):
    bl_label = "xBake Setup"
    bl_idname = "VIEW3D_PT_smart_baking"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'xBake'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        bake_settings = scene.smart_bake_settings
        
        allowBake = True
        

        layout.label(text="Bake Type", icon="MOD_EXPLODE")
        row = layout.row(align=True)
        row.prop(bake_settings, "selected_to_active", text="Source to Target", icon='LINKED')
        row.prop(bake_settings, "single_object", text="Single Object", icon='CUBE')
        
        if bake_settings.selected_to_active:
            layout.prop(bake_settings, "source_object", text="Source")
            layout.prop(bake_settings, "target_object", text="Target")
            
            layout.separator()
            layout.label(text="Projection Settings", icon="PROP_PROJECTED")
            
            layout.prop(bake_settings, "cage", text="Use Cage")
            if bake_settings.cage:
                layout.prop(bake_settings, "cage_object", text="Cage Object")
                layout.prop(bake_settings, "extrusion", text="Cage Extrusion", slider=True)
            else:
                layout.prop(bake_settings, "extrusion", text="Extrusion", slider=True)
            layout.prop(bake_settings, "max_ray_distance", text="Max Ray Distance", slider=True)
        else:
            layout.prop(bake_settings, "target_object", text="Target")
        
        layout.separator()
        layout.label(text="Bake Outputs", icon="MOD_UVPROJECT")
        
        box = layout.box()
        
        # Unlit Maps section
        icon_cola = 'TRIA_DOWN' if bake_settings.expand_cola else 'TRIA_RIGHT'
        box.prop(bake_settings, "expand_cola", icon=icon_cola, text="Unlit Maps (Material Independent)", emboss=False)
        if bake_settings.expand_cola:
            cola = box.column()

        
            cola.prop(bake_settings, "normal", text="Normal", icon='NORMALS_VERTEX')
            if bake_settings.normal:
                cola.prop(bake_settings, "normal_format", text='Format')
                cola.separator()
                
            cola.prop(bake_settings, "ambient_occlusion", text="Ambient Occlusion", icon='WORLD')
            
            cola.prop(bake_settings, "curvature", text="Curvature", icon='CURVE_NCURVE')
            if bake_settings.curvature:
                cola.prop(bake_settings, "curvaturecontrast", text="Curvature Contrast", slider=True)
                cola.separator()
            
            cola.prop(bake_settings, "uv", text="UV", icon='GROUP_UVS')
            if bake_settings.uv:
                cola.prop(bake_settings, "UVOpacity", text="UV Opacity", slider=True)
                cola.separator()
            
            
            cola.prop(bake_settings, "position", text="Position", icon='EMPTY_ARROWS')
            cola.prop(bake_settings, "worldspacenormal", text="World Space Normal", icon='ORIENTATION_NORMAL')
            
            if bake_settings.position or bake_settings.worldspacenormal:
                cola.label(text="Coordinate Swizzle")
                cola.prop(bake_settings, "forward_axis")
                cola.prop(bake_settings, "up_axis")

            cola.separator()
        
        # Lit Maps section
        icon_colb = 'TRIA_DOWN' if bake_settings.expand_colb else 'TRIA_RIGHT'
        box.prop(bake_settings, "expand_colb", icon=icon_colb, text="Lit Maps (Material Dependent)", emboss=False)
        if bake_settings.expand_colb:
            colb = box.column()
            colb.label(text="Light Contributions")
            row = colb.row(align=True)
            row.prop(bake_settings, "direct", text="Direct", icon='LIGHT')
            row.prop(bake_settings, "indirect", text="Indirect", icon='LIGHT_SUN')
            row.prop(bake_settings, "color", text="Color", icon='COLOR')
            
            colb.separator()
            colb.prop(bake_settings, "combined", text="Combined", icon='TEXTURE')
            colb.prop(bake_settings, "diffuse", text="Diffuse", icon='MATERIAL')
            colb.prop(bake_settings, "roughness", text="Roughness", icon='MATSPHERE')
            colb.prop(bake_settings, "glossy", text="Glossy", icon='SHADING_TEXTURE')
            colb.prop(bake_settings, "emit", text="Emit", icon='LIGHT_POINT')
            colb.prop(bake_settings, "transmission", text="Transmission", icon='INDIRECT_ONLY_OFF')
            colb.prop(bake_settings, "shadow", text="Shadow", icon='SHADING_RENDERED')
            colb.prop(bake_settings, "environment", text="Environment", icon='WORLD')


class BakeSenseOutput(bpy.types.Panel):
    bl_label = "xBake Output"
    bl_idname = "VIEW3D_PT_smart_bake_output"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'xBake'
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        bake_settings = scene.smart_bake_settings
        cycles = scene.cycles
        
        allowBake = True
                
        map_types = [
            ("normal", "NORMAL"),
            ("ambient_occlusion", "AO"),
            ("curvature", "CURVATURE"), 
            ("uv", "UV"),
            ("position", "POSITION"),
            ("worldspacenormal", "WORLD_SPACE_NORMAL"),
            ("combined", "COMBINED"),
            ("shadow", "SHADOW"),
            ("roughness", "ROUGHNESS"),
            ("emit", "EMIT"),
            ("environment", "ENVIRONMENT"),
            ("diffuse", "DIFFUSE"),
            ("glossy", "GLOSSY"),
            ("transmission", "TRANSMISSION")
        ]
        
        isValidSelection = False
        for prop_name, bake_type in map_types:
            if getattr(bake_settings, prop_name):
                isValidSelection = True
#                if bake_type == "NORMAL" or bake_type == "AO" or bake_type == "CURVATURE" or bake_type == "POSITION" or bake_type == "WORLD_SPACE_NORMAL" or bake_type == "UV":
#                    islitmap = False
        
        missingSource = False   
        if isValidSelection:  
            if bake_settings.target_object:
                if bake_settings.selected_to_active:
                    if bake_settings.source_object == None:
                        missingsource = True
                        layout.label(text="Define a source object in xBake Setup, or use Single Object mode", icon="ERROR")
                        allowBake = False
            else:
                layout.label(text="Define a target object in xBake Setup", icon="ERROR")
                allowBake = False
            
        else:
            layout.label(text="Select at least one bake output in xBake Setup > Bake Outputs", icon="ERROR")
            allowBake = False
        
        if isValidSelection:
            if not missingSource:
                double_button = layout.row()
                double_button.scale_y = 2.0  # Scale the height of the button
                double_button.operator("smart_bake.bake_selected_maps", icon='RENDER_STILL')
                
#                out_file_ex = bpy.path.abspath(CreateMapOutput('DIFFUSE'))
#                out_dir = os.path.dirname(out_file_ex)
#                if os.path.exists(out_dir):
#                    icon = 'FOLDER_REDIRECT'
#                else:
#                    icon = 'NEW_FOLDER'
#                    
#                row=layout.row(align=True)
#                row.label(text=bpy.path.relpath(out_dir))
#                row.operator("file.open_or_create_folder", text="Open Output Directory", icon=icon).path = out_dir
        
        layout.separator()
        
        if allowBake:
            layout.label(text="Baking allowed")
            
            layout.prop(bake_settings, "resolution", text="Resolution")
            
            # Display Cycles rendering properties
            layout.prop(cycles, "samples", text="Render Samples")
            layout.prop(cycles, "adaptive_min_samples", text="Adaptive Min Samples")
            layout.prop(cycles, "time_limit", text="Render Time Limit (seconds)")
            
            layout.separator()
            layout.prop(bake_settings, "margin_type", text="Margin Type")
            value = bpy.context.scene.render.bake.margin
            layout.prop(bake_settings, "margin_percentage", text="Bake Margin   |   " + str(value) + "px")
            layout.separator()
            layout.label(text="Output Structure")
            row = layout.row(align=True)
            row.prop(bake_settings, "automatic_output_path", text="Automatic", icon="DECORATE_LOCKED")
            row.prop(bake_settings, "custom_output_path", text="Custom", icon="DECORATE_UNLOCKED")
            obj = bake_settings.target_object
            
            if not bake_settings.single_object:
                src = bake_settings.source_object
            else:
                src = None
                
            labelText = ""
            
            name="temp"
        
            if obj:
                name = obj.name # name based on single object name if single-object bake
                if src:
                    # Name based on common prefix if source to target bake
                    source_name = bake_settings.source_object.name
                    common_name = os.path.commonprefix([source_name, name])
                    name = re.sub(r'[^a-zA-Z0-9]+$', '', common_name)  # Strip any trailing characters that are not letters or numbers
            
            if not bake_settings.automatic_output_path:
                if bake_settings.use_custom_name:
                    if name != "":
                        name = bake_settings.custom_name
                    else:
                        name="custom_name"
                    
            if bake_settings.automatic_output_path:
                output_dir = bpy.path.abspath(f"//Resources/{name}/baked_maps/")
            else:
                top_box = layout.box()
                top_box.label(text="Custom Output Settings", icon="SETTINGS")
                row = top_box.row(align=True)
                row.prop(bake_settings, "use_custom_path", text="Define Path")
                if bake_settings.use_custom_path:
                    row.prop(bake_settings, "bake_path", text="")
                    output_dir = bake_settings.bake_path
                    if bake_settings.bake_path == "":
                        top_box.label(text="Please define an output path")
                        allowBake = False
                else:
                    # custom, but not custom path
                    output_dir = bpy.path.abspath(f"//Resources/")
            

            if bake_settings.custom_output_path:
                row = top_box.row(align = True)
                row.prop(bake_settings, "use_custom_name", text="Define Name")
                if bake_settings.use_custom_name:
                    row.prop(bake_settings, "custom_name", text="")
                
                row = top_box.row()
                row.prop(bake_settings, "use_object_folder", text="Use Object Folder" + " (" +name+")", icon="FILE_FOLDER")
                
                row = top_box.row(align=True)
                row.prop(bake_settings, "use_subfolder", text="Use Sub-Folder", icon="FILE_FOLDER")
                row.prop(bake_settings, "subfolder_name", text="")
                
                
                row = top_box.separator()
                top_box.label(text="Naming Conventions")
                        
                row = top_box.row(align = True)
                row.prop(bake_settings, "naming_uppercase", text="Uppercase")
                row.prop(bake_settings, "naming_lowercase", text="Lowercase")
                row.prop(bake_settings, "naming_pascalcase", text="Pascal Case")
                
                top_box.label(text="Separators")
                row = top_box.row()
                row.prop(bake_settings, "naming_separator", text="After Name")
                row = top_box.row()
                row.prop(bake_settings, "mapname_separator", text="Within Baketype")
            
            row = layout.row()
            row.prop(bake_settings, "show_hierarchy", text="Show Output Structure", icon="RNA")
            
            if bake_settings.automatic_output_path:
                separator2 = "_"
            else:
                separator2 = bake_settings.mapname_separator
                
                if bake_settings.naming_pascalcase:
                    separator2 = "."
                        
            if bake_settings.show_hierarchy:
                
                # Select at least one output
                map_types = [
                    ("combined", "COMBINED"),
                    ("normal", "NORMAL"),
                    ("ambient_occlusion", "AMBIENT" + separator2 + "OCCLUSION"),
                    ("shadow", "SHADOW"),
                    ("position", "POSITION"),
                    ("uv", "UV"),
                    ("roughness", "ROUGHNESS"),
                    ("emit", "EMIT"),
                    ("environment", "ENVIRONMENT"),
                    ("diffuse", "DIFFUSE"),
                    ("glossy", "GLOSSY"),
                    ("transmission", "TRANSMISSION"),
                    ("curvature", "CURVATURE"),  # Add curvature as a special case
                    ("worldspacenormal", "WORLD" + separator2 + "SPACE" + separator2 + "NORMALS")
                ]
                
                if bake_settings.automatic_output_path:
                    last_part = os.path.basename(os.path.normpath(output_dir))
                    blend_file_dir = os.path.dirname(bpy.data.filepath)
                    folder_name = os.path.basename(blend_file_dir)
                    blend_file_path = bpy.data.filepath
                    blend_file_name = os.path.basename(blend_file_path)
                    
                    # Automatic Structure
                    top_box = layout.box()
                    col = top_box.column()
                    col.label(text="Resources", icon="FILE_FOLDER")

                    # Indentation level 1 within a nested box
                    box1 = col.box()
                    col1 = box1.column()
#                    col1.label(text=blend_file_name, icon="BLENDER")
                    col1.label(text=name, icon="FILE_FOLDER")

                    # Indentation level 2 within another nested box
                    box2 = col1.box()
                    col2 = box2.column()
                    col2.label(text=last_part, icon="FILE_FOLDER")

                    # Indentation level 3 within yet another nested box
                    box3 = col2.box()
                    col3 = box3.column(align=True)
                    for prop_name, bake_type in map_types:
                        if getattr(bake_settings, prop_name):
                            bake_type_formatted = bake_type.lower()
                            col3.label(text=name + "_" + bake_type_formatted, icon="FILE_IMAGE")

                else:
                    folder_path = os.path.dirname(output_dir)
                    folder_name = os.path.basename(folder_path)
                    
                    # User-defined structure
                    top_box = layout.box()
                    col = top_box.column()
                    col.label(text=folder_name, icon="FILE_FOLDER")
                    
                    if bake_settings.use_object_folder:
                        if bake_settings.use_subfolder:
                            box1 = col.box()
                            col1 = box1.column()
                            col1.label(text=name, icon="FILE_FOLDER")
                                                # Indentation level 2 within another nested box
                            box2 = col1.box()
                            col2 = box2.column()
                            col2.label(text=bake_settings.subfolder_name, icon="FILE_FOLDER")
                        
                            box3 = col2.box()
                            col3 = box3.column(align=True)
                            for prop_name, bake_type in map_types:
                                if getattr(bake_settings, prop_name):
                                    if not bake_settings.naming_uppercase and not bake_settings.naming_pascalcase:
                                        bake_type_formatted = bake_type.lower()
                                    elif bake_settings.naming_uppercase:
                                        bake_type_formatted = bake_type
                                    elif bake_settings.naming_pascalcase:
                                        words = bake_type.lower().split(".")
                                        bake_type_formatted = ''.join(word.capitalize() + "." for word in words).replace(".", bake_settings.mapname_separator)
                                        if len(bake_settings.mapname_separator) > 0:
                                            bake_type_formatted = bake_type_formatted[:-len(bake_settings.mapname_separator)]
                                    
                                    col3.label(text=name + bake_settings.naming_separator + bake_type_formatted, icon="FILE_IMAGE")
                            
                        else:
                            box1 = col.box()
                            col1 = box1.column()
                            col1.label(text=name, icon="FILE_FOLDER")
                            box2 = col1.box()
                            col2 = box2.column(align=True)
                        
                            for prop_name, bake_type in map_types:
                                if getattr(bake_settings, prop_name):
                                    if not bake_settings.naming_uppercase and not bake_settings.naming_pascalcase:
                                        bake_type_formatted = bake_type.lower()
                                    elif bake_settings.naming_uppercase:
                                        bake_type_formatted = bake_type
                                    elif bake_settings.naming_pascalcase:
                                        words = bake_type.lower().split(".")
                                        bake_type_formatted = ''.join(word.capitalize() + "." for word in words).replace(".", bake_settings.mapname_separator)
                                        if len(bake_settings.mapname_separator) > 0:
                                            bake_type_formatted = bake_type_formatted[:-len(bake_settings.mapname_separator)]
                                    
                                    col2.label(text=name + bake_settings.naming_separator + bake_type_formatted, icon="FILE_IMAGE")
                    
                    else: # not using object folder
                        box1 = col.box()
                        col1 = box1.column(align=True)
                        
                        if bake_settings.use_subfolder:
                            col1.label(text=bake_settings.subfolder_name, icon="FILE_FOLDER")
                            box2 = col1.box()
                            col2 = box2.column(align=True)
                            
                            for prop_name, bake_type in map_types:
                                if getattr(bake_settings, prop_name):
                                    if not bake_settings.naming_uppercase and not bake_settings.naming_pascalcase:
                                        bake_type_formatted = bake_type.lower()
                                    elif bake_settings.naming_uppercase:
                                        bake_type_formatted = bake_type
                                    elif bake_settings.naming_pascalcase:
                                        words = bake_type.lower().split(".")
                                        bake_type_formatted = ''.join(word.capitalize() + "." for word in words).replace(".", bake_settings.mapname_separator)
                                        if len(bake_settings.mapname_separator) > 0:
                                            bake_type_formatted = bake_type_formatted[:-len(bake_settings.mapname_separator)]
                                    
                                    col2.label(text=name + bake_settings.naming_separator + bake_type_formatted, icon="FILE_IMAGE")

                        
                        else:
                            for prop_name, bake_type in map_types:
                                if getattr(bake_settings, prop_name):
                                    if not bake_settings.naming_uppercase and not bake_settings.naming_pascalcase:
                                        bake_type_formatted = bake_type.lower()
                                    elif bake_settings.naming_uppercase:
                                        bake_type_formatted = bake_type
                                    elif bake_settings.naming_pascalcase:
                                        words = bake_type.lower().split(".")
                                        bake_type_formatted = ''.join(word.capitalize() + "." for word in words).replace(".", bake_settings.mapname_separator)
                                        if len(bake_settings.mapname_separator) > 0:
                                            bake_type_formatted = bake_type_formatted[:-len(bake_settings.mapname_separator)]
                                    
                                    col1.label(text=name + bake_settings.naming_separator + bake_type_formatted, icon="FILE_IMAGE")
            

def open_folder(path):
    """Open folder in the system's default file explorer."""
    if os.path.isdir(path):
        if os.name == 'nt':  # Windows
            subprocess.Popen(f'explorer "{path}"')
        elif os.name == 'posix':
            if 'Darwin' in os.uname().sysname:  # macOS
                subprocess.Popen(['open', path])
            else:  # Linux
                subprocess.Popen(['xdg-open', path])
                
class OpenOrCreateFolderOperator(bpy.types.Operator):
    """Operator to open or create a directory in the system's file explorer"""
    bl_idname = "file.open_or_create_folder"
    bl_label = "Open or Create Folder"
    
    path: bpy.props.StringProperty(name="Path", description="Absolute directory path", default="")

    def execute(self, context):
        if not self.path:
            self.report({'ERROR'}, "No path specified")
            return {'CANCELLED'}
        
        if not os.path.exists(self.path):
            # Create the directory
            os.makedirs(self.path)
        
        # Open the folder in the system explorer
        open_folder(self.path)
        
        return {'FINISHED'}
    
    def draw(self, context):
        """Draw UI elements based on path existence."""
        layout = self.layout
        if os.path.exists(self.path):
            icon = 'FOLDER_REDIRECT'
        else:
            icon = 'NEW_FOLDER'
        layout.operator("file.open_or_create_folder", icon=icon).path = self.path
   
def CreateMapOutput(bakeType):
    scene = bpy.context.scene
    bake_settings = scene.smart_bake_settings

    # Find Name
    obj = bake_settings.target_object
    if not bake_settings.single_object:
        src = bake_settings.source_object
    else:
        src = None
    if obj:
        name = obj.name
        if src:
            source_name = bake_settings.source_object.name
            common_name = os.path.commonprefix([source_name, name])
            name = re.sub(r'[^a-zA-Z0-9]+$', '', common_name)
    
    # Create Standard Output
    output_dir = bpy.path.abspath(f"//Resources/{name}/baked_maps/")
    root_path = bpy.path.abspath(f"//Resources/")
    
    if bake_settings.automatic_output_path:
        separator2 = "_"
    else: # Custom Output
        if bake_settings.use_custom_name:
            name = bake_settings.custom_name
        separator2 = bake_settings.mapname_separator
        if bake_settings.naming_pascalcase:
            separator2 = "."
        
        if bake_settings.use_custom_path:
            output_dir = bake_settings.bake_path
            if bake_settings.use_object_folder:
                output_dir = os.path.join(output_dir, name)
                if bake_settings.use_subfolder:
                    output_dir = os.path.join(output_dir, bake_settings.subfolder_name)
            else:
                if bake_settings.use_subfolder:
                    output_dir = os.path.join(output_dir, bake_settings.subfolder_name)
        else:
            output_dir = root_path
            if bake_settings.use_object_folder:
                output_dir = os.path.join(output_dir, name)
                if bake_settings.use_subfolder:
                    output_dir = os.path.join(output_dir, bake_settings.subfolder_name)
            else:
                if bake_settings.use_subfolder:
                    output_dir = os.path.join(output_dir, bake_settings.subfolder_name)
        
    output_dir = bpy.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    map_types = [
        ("COMBINED", "COMBINED"),
        ("NORMAL", "NORMAL"),
        ("AO", "AMBIENT" + separator2 + "OCCLUSION"),
        ("SHADOW", "SHADOW"),
        ("POSITION", "POSITION"),
        ("UV", "UV"),
        ("ROUGHNESS", "ROUGHNESS"),
        ("EMIT", "EMIT"),
        ("ENVIRONMENT", "ENVIRONMENT"),
        ("DIFFUSE", "DIFFUSE"),
        ("GLOSSY", "GLOSSY"),
        ("TRANSMISSION", "TRANSMISSION"),
        ("CURVATURE", "CURVATURE"),  # Add curvature as a special case
        ("WORLD_SPACE_NORMAL", "WORLD" + separator2 + "SPACE" + separator2 + "NORMALS")
    ]
    
    selected_type = None
    
    for prop_name, bake_type in map_types:
        if bakeType == prop_name:
            selected_type = bake_type
            break
    
    if bake_settings.automatic_output_path: # Auto Output
        bake_type_formatted = selected_type.lower()
    
    else: # Custom Settings
        if not bake_settings.naming_uppercase and not bake_settings.naming_pascalcase:
            bake_type_formatted = selected_type.lower()
        elif bake_settings.naming_uppercase:
            bake_type_formatted = selected_type
        elif bake_settings.naming_pascalcase:
            words = selected_type.lower().split(".")
            bake_type_formatted = ''.join(word.capitalize() + "." for word in words).replace(".", bake_settings.mapname_separator)
            if len(bake_settings.mapname_separator) > 0:
                bake_type_formatted = bake_type_formatted[:-len(bake_settings.mapname_separator)]
    
    full_name = name + bake_settings.naming_separator + bake_type_formatted
    output_file = os.path.join(output_dir, full_name + ".png")
    
    # Return the directory path
    return output_file

def process_directx_normal(image_filepath):
    # Store current scene for later
    original_scene = bpy.context.scene

    # Create a new scene
    new_scene = bpy.data.scenes.new("normal_composite_temp")
    bpy.context.window.scene = new_scene

    # Disable rendering for the new scene's ViewLayer
    new_scene.view_layers["ViewLayer"].use = False

    # Set view transform to 'Standard'
#    new_scene.render.image_settings.color_management = 'OVERRIDE'
    new_scene.view_settings.view_transform = 'Raw'
    new_scene.render.image_settings.compression = 0
    new_scene.eevee.taa_samples = 0
    
    # Enable compositing and use nodes
    new_scene.use_nodes = True
    node_tree = new_scene.node_tree

    # Clear default nodes
    for node in node_tree.nodes:
        node_tree.nodes.remove(node)

    # Create image node
    image_node = node_tree.nodes.new(type='CompositorNodeImage')
    image_node.image = bpy.data.images.load(image_filepath)
    image_node.image.colorspace_settings.name = 'Non-Color'

    # Ensure the rendered output is the same resolution as the loaded image
    new_scene.render.resolution_x = image_node.image.size[0]
    new_scene.render.resolution_y = image_node.image.size[1]

    # Set output to 16-bit depth
    new_scene.render.image_settings.color_depth = '16'

    # Create Separate XYZ node
    separate_xyz_node = node_tree.nodes.new(type='CompositorNodeSeparateXYZ')

    # Create Math node (subtract)
    math_node = node_tree.nodes.new(type='CompositorNodeMath')
    math_node.operation = 'SUBTRACT'
    math_node.inputs[0].default_value = 1  # Set the first input value to 1

    # Create Combine XYZ node
    combine_xyz_node = node_tree.nodes.new(type='CompositorNodeCombineXYZ')

    # Create Composite output node
    composite_node = node_tree.nodes.new(type='CompositorNodeComposite')

    # Connect nodes
    links = node_tree.links
    links.new(image_node.outputs["Image"], separate_xyz_node.inputs[0])
    links.new(separate_xyz_node.outputs["X"], combine_xyz_node.inputs["X"])
    links.new(separate_xyz_node.outputs["Z"], combine_xyz_node.inputs["Z"])
    links.new(separate_xyz_node.outputs["Y"], math_node.inputs[1])
    links.new(math_node.outputs[0], combine_xyz_node.inputs["Y"])
    links.new(combine_xyz_node.outputs[0], composite_node.inputs[0])
    links.new(image_node.outputs["Alpha"], composite_node.inputs[1])
    
    # Update the scene context to ensure all changes are registered
    bpy.context.view_layer.update()
    node_tree.update_tag()
    bpy.context.view_layer.update()

    # Render and save over the original image, ensuring the new scene is active
    bpy.context.window.scene = new_scene  # Explicitly set the scene for rendering
    bpy.ops.render.render(write_still=True)

    # Render and save over the original image
    bpy.context.window.scene = new_scene

    bpy.context.scene.render.filepath = image_filepath
    bpy.ops.render.render(write_still=True)

    # Cleanup
    bpy.context.window.scene = original_scene
    bpy.data.images.remove(image_node.image)
    bpy.data.scenes.remove(new_scene)

    print("Normal Map converted to DirectX format.")
    
def process_swizzle(image_filepath):
    # Store current scene for later
    original_scene = bpy.context.scene

    # Create a new scene
    new_scene = bpy.data.scenes.new("swizzle_composite_temp")
    bpy.context.window.scene = new_scene

    # Disable rendering for the new scene's ViewLayer
    new_scene.view_layers["ViewLayer"].use = False

    # Set view transform to 'Standard'
#    new_scene.render.image_settings.color_management = 'OVERRIDE'
    new_scene.view_settings.view_transform = 'Raw'
    new_scene.render.image_settings.compression = 0
    new_scene.eevee.taa_samples = 0
    
    # Enable compositing and use nodes
    new_scene.use_nodes = True
    node_tree = new_scene.node_tree

    # Clear default nodes
    for node in node_tree.nodes:
        node_tree.nodes.remove(node)

    # Create image node
    image_node = node_tree.nodes.new(type='CompositorNodeImage')
    image_node.image = bpy.data.images.load(image_filepath)
    image_node.image.colorspace_settings.name = 'Non-Color'

    # Ensure the rendered output is the same resolution as the loaded image
    new_scene.render.resolution_x = image_node.image.size[0]
    new_scene.render.resolution_y = image_node.image.size[1]

    # Set output to 16-bit depth
    new_scene.render.image_settings.color_depth = '16'

    # Create Separate XYZ node
    separate_xyz_node = node_tree.nodes.new(type='CompositorNodeSeparateXYZ')
    
    #
    #
    #

    # Create Math node (subtract)
    math_node_x = node_tree.nodes.new(type='CompositorNodeMath')
    math_node_x.operation = 'SUBTRACT'
    math_node_x.inputs[0].default_value = 1  # Set the first input value to 1
    
    math_node_y = node_tree.nodes.new(type='CompositorNodeMath')
    math_node_y.operation = 'SUBTRACT'
    math_node_y.inputs[0].default_value = 1  # Set the first input value to 1
    
    math_node_z = node_tree.nodes.new(type='CompositorNodeMath')
    math_node_z.operation = 'SUBTRACT'
    math_node_z.inputs[0].default_value = 1  # Set the first input value to 1

    # Create Combine XYZ node
    combine_xyz_node = node_tree.nodes.new(type='CompositorNodeCombineXYZ')

    # Create Composite output node
    composite_node = node_tree.nodes.new(type='CompositorNodeComposite')
    
    #
    #
    #

    # Connect nodes
    links = node_tree.links
    links.new(image_node.outputs["Image"], separate_xyz_node.inputs[0])
    links.new(separate_xyz_node.outputs["X"], combine_xyz_node.inputs["X"])
    links.new(separate_xyz_node.outputs["Z"], combine_xyz_node.inputs["Z"])
    links.new(separate_xyz_node.outputs["Y"], math_node.inputs[1])
    links.new(math_node.outputs[0], combine_xyz_node.inputs["Y"])
    links.new(combine_xyz_node.outputs[0], composite_node.inputs[0])
    links.new(image_node.outputs["Alpha"], composite_node.inputs[1])
    
    # Update the scene context to ensure all changes are registered
    bpy.context.view_layer.update()
    node_tree.update_tag()
    bpy.context.view_layer.update()

    # Render and save over the original image, ensuring the new scene is active
    bpy.context.window.scene = new_scene  # Explicitly set the scene for rendering
    bpy.ops.render.render(write_still=True)

    # Render and save over the original image
    bpy.context.window.scene = new_scene

    bpy.context.scene.render.filepath = image_filepath
    bpy.ops.render.render(write_still=True)

    # Cleanup
    bpy.context.window.scene = original_scene
    bpy.data.images.remove(image_node.image)
    bpy.data.scenes.remove(new_scene)

    print("Normal Map converted to DirectX format.")

    

class BakeSelectedMapsOperator(bpy.types.Operator):
    bl_idname = "smart_bake.bake_selected_maps"
    bl_label = "Bake"

    def execute(self, context):

        map_types = [
            ("normal", "NORMAL"),
            ("ambient_occlusion", "AO"),
            ("curvature", "CURVATURE"), 
            ("uv", "UV"),
            ("position", "POSITION"),
            ("worldspacenormal", "WORLD_SPACE_NORMAL"),
            ("combined", "COMBINED"),
            ("shadow", "SHADOW"),
            ("roughness", "ROUGHNESS"),
            ("emit", "EMIT"),
            ("environment", "ENVIRONMENT"),
            ("diffuse", "DIFFUSE"),
            ("glossy", "GLOSSY"),
            ("transmission", "TRANSMISSION")
        ]
        
        scene = bpy.context.scene
        bake_settings = scene.smart_bake_settings
        
        islitmap = True
        for prop_name, bake_type in map_types:
            if getattr(bake_settings, prop_name):
                if bake_type == "NORMAL" or bake_type == "AO" or bake_type == "CURVATURE" or bake_type == "POSITION" or bake_type == "WORLD_SPACE_NORMAL" or bake_type == "UV":
                    islitmap = False
                
        if islitmap:
            source = bake_settings.source_object
            target = bake_settings.target_object
        else:
            source = bake_settings.source_object.copy()
            source.data = bake_settings.source_object.data.copy()
            bpy.context.collection.objects.link(source)
            
            target = bake_settings.target_object.copy()
            target.data = bake_settings.target_object.data.copy()
            bpy.context.collection.objects.link(target)
            
            sourceref = source
            targetref = target
            
            bake_settings.source_object.hide_render = True
            bake_settings.target_object.hide_render = True
            source.data.materials.clear()
            target.data.materials.clear()
            
        # Setup source to target
        for object in bpy.context.view_layer.objects:
            if object == source:
                source.select_set(True)
            elif object == target:
                target.select_set(True)
                bpy.context.view_layer.objects.active = target
            else:
                object.select_set(False)
        
        obj = context.active_object
        non_active_obj = None
        user_obj = obj
        
        if obj is None:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}
        
        # Ensure only two objects are selected
        if len(bpy.context.selected_objects) == 2:
            # Get the active object
            active_obj = bpy.context.active_object

            # Get the other selected object (non-active)
            non_active_obj = next(obj for obj in bpy.context.selected_objects if obj != active_obj)
            user_obj = non_active_obj
        
        scene.render.bake.use_selected_to_active = bake_settings.selected_to_active
        
        scene.render.bake.use_pass_direct = bake_settings.direct
        scene.render.bake.use_pass_indirect = bake_settings.indirect
        bpy.context.scene.render.bake.use_pass_color = bake_settings.color
        scene.render.bake.use_cage = bake_settings.cage
        bpy.context.scene.render.bake.cage_object = bake_settings.cage_object
        scene.render.bake.cage_extrusion = bake_settings.extrusion
        scene.render.bake.max_ray_distance = bake_settings.max_ray_distance
        
        # Ensure Cycles is set
        default_engine = bpy.context.scene.render.engine
        bpy.context.scene.render.engine = 'CYCLES'
        
        # Ensure there is at least one material slot and a material assigned to it
        if not obj.data.materials or not obj.active_material:
            # Create a new material and assign it to the first slot
            mat = bpy.data.materials.new(name=f"{obj.name}_Material")
            if obj.data.materials:
                obj.data.materials[0] = mat  # Set the material in the existing slot
            else:
                obj.data.materials.append(mat)  # Add the material to a new slot
        else:
            mat = obj.active_material  # Use the existing active material
        
        mat.use_nodes = True
        # Ensure the material is assigned as the object's active material
        user_obj.active_material = mat

        original_material = mat  # Save the original material
        copydestroyed = False
        
        for prop_name, bake_type in map_types:
            if getattr(bake_settings, prop_name):
                
                islitcurrent = True
                if bake_type == "NORMAL" or bake_type == "AO" or bake_type == "CURVATURE" or bake_type == "POSITION" or bake_type == "WORLD_SPACE_NORMAL" or bake_type == "UV":
                    islitcurrent = False
                if islitcurrent:
                    copydestroyed = True
                    if source != bake_settings.source_object:
                        source = bake_settings.source_object
                        target = bake_settings.target_object
                        # Setup source to target
                        for object in bpy.context.view_layer.objects:
                            if object == source:
                                source.select_set(True)
                            elif object == target:
                                target.select_set(True)
                                bpy.context.view_layer.objects.active = target
                            else:
                                object.select_set(False)
                                if object == sourceref:
                                    bpy.data.objects.remove(sourceref)
                                if object == targetref:
                                    bpy.data.objects.remove(targetref)
                                    
                        obj = context.active_object
                        non_active_obj = None
                        user_obj = obj
                        bake_settings.source_object.hide_render = False
                        bake_settings.target_object.hide_render = False
                        if obj is None:
                            self.report({'ERROR'}, "No active object selected")
                            return {'CANCELLED'}
                        
                        # Ensure only two objects are selected
                        if len(bpy.context.selected_objects) == 2:
                            # Get the active object
                            active_obj = bpy.context.active_object

                            # Get the other selected object (non-active)
                            non_active_obj = next(obj for obj in bpy.context.selected_objects if obj != active_obj)
                            user_obj = non_active_obj
            
                        # Ensure there is at least one material slot and a material assigned to it
                        if not obj.data.materials or not obj.active_material:
                            # Create a new material and assign it to the first slot
                            mat = bpy.data.materials.new(name=f"{obj.name}_Material")
                            if obj.data.materials:
                                obj.data.materials[0] = mat  # Set the material in the existing slot
                            else:
                                obj.data.materials.append(mat)  # Add the material to a new slot
                        else:
                            mat = obj.active_material  # Use the existing active material
            
                if bake_type == "UV":
                    # Select only the target
                    for obj in bpy.context.view_layer.objects:
                        obj.select_set(obj == target)
                    bpy.context.view_layer.objects.active = target

                    # Switch to EDIT mode and select everything for UV export
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')
                    bpy.ops.uv.select_all(action='SELECT')

                    # Export UV layout to a specific path
                    export_path = CreateMapOutput(bake_type)  # Define your filepath clearly
                    bpy.ops.uv.export_layout(filepath=export_path, size=(bake_settings.resolution, bake_settings.resolution), opacity = bake_settings.UVOpacity)

                    # Switch back to OBJECT mode
                    bpy.ops.object.mode_set(mode='OBJECT')

                    # Re-select the source and target as needed
                    for obj in bpy.context.view_layer.objects:
                        obj.select_set(obj in [source, target])
                    bpy.context.view_layer.objects.active = target
                    
                elif bake_type == "CURVATURE":
                    # Create a temporary curvature material
                    curvature_material = bpy.data.materials.new(name="Temp_Curvature_Material")
                    curvature_material.use_nodes = True
                    nodes = curvature_material.node_tree.nodes
                    links = curvature_material.node_tree.links
                    img_nodes = mat.node_tree.nodes

                    # Set up nodes for curvature bake
                    geometry_node = nodes.new("ShaderNodeNewGeometry")
                    map_range_node = nodes.new("ShaderNodeMapRange")
                    map_range_node.inputs["From Min"].default_value = 0.5 - (((1 - bake_settings.curvaturecontrast)/2)+.001)
                    map_range_node.inputs["From Max"].default_value = 0.5 + (((1 - bake_settings.curvaturecontrast)/2)+.001)

                    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
                    output_node = nodes.get("Material Output")

                    links.new(geometry_node.outputs["Pointiness"], map_range_node.inputs["Value"])
                    links.new(map_range_node.outputs["Result"], bsdf_node.inputs["Base Color"])
                    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

                    # Assign the temporary material
                    user_obj.data.materials[0] = curvature_material

                    # Create an image for the curvature bake
                    img_name = f"{obj.name}_CURVATURE"
                    img = bpy.data.images.new(name=img_name, width=bake_settings.resolution, height=bake_settings.resolution, float_buffer=True)
                    img.colorspace_settings.name = 'Non-Color'

                    # Fill the image with 0.5 gray by setting every pixel to (0.5, 0.5, 0.5, 1.0)
                    # 'pixels' is a flat array where each RGBA component is sequentially arranged
                    img.pixels = [0.5, 0.5, 0.5, 1.0] * (bake_settings.resolution ** 2)
                    img.filepath_raw = CreateMapOutput(bake_type)
                    img.file_format = 'PNG'
                    bpy.context.scene.render.bake.use_clear = False
                    # Assign the image to the bake
                    if bake_settings.selected_to_active == True:
                        img_node = img_nodes.new("ShaderNodeTexImage")
                    else:
                        img_node = nodes.new("ShaderNodeTexImage")
                    
                    img_node.image = img
                    nodes.active = img_node

                    # Bake the curvature as diffuse
                    bpy.context.scene.cycles.bake_type = 'DIFFUSE'
                    bpy.context.scene.render.bake.use_pass_direct = False
                    bpy.context.scene.render.bake.use_pass_indirect = False
                    bpy.ops.object.bake(type='DIFFUSE')

                    # Save and cleanup
                    img.save()
                    bpy.context.scene.render.bake.use_clear = True
                    bpy.data.images.remove(img)

                    if bake_settings.selected_to_active == True:
                        img_nodes.remove(img_node)
                    else:
                        nodes.remove(img_node)
                    bpy.data.materials.remove(curvature_material)
                    
                    # Restore the original material
                    user_obj.data.materials[0] = original_material
                    bpy.context.scene.render.bake.use_pass_direct = bake_settings.direct
                    bpy.context.scene.render.bake.use_pass_indirect = bake_settings.indirect
                
                elif bake_type == "WORLD_SPACE_NORMAL":
                    # Create a temporary curvature material
                    
                    #
                    #
                    #
                    # Create the world space normal material
                    wsn_material = bpy.data.materials.new(name="Temp_WSN_Material")
                    wsn_material.use_nodes = True
                    node_tree = wsn_material.node_tree
                    nodes = wsn_material.node_tree.nodes
                    links = wsn_material.node_tree.links
                    img_nodes = mat.node_tree.nodes

                    # Clear default nodes for clarity
                    for node in nodes:
                        nodes.remove(node)

                    # Create necessary nodes
                    geometry_node = nodes.new("ShaderNodeNewGeometry")
                    separate_xyz_node = nodes.new("ShaderNodeSeparateXYZ")
                    map_range_x = nodes.new("ShaderNodeMapRange")
                    map_range_y = nodes.new("ShaderNodeMapRange")
                    map_range_z = nodes.new("ShaderNodeMapRange")
                    combine_xyz_node = nodes.new("ShaderNodeCombineXYZ")
                    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
                    output_node = nodes.new("ShaderNodeOutputMaterial")

                    # Set up node locations (optional for better layout visualization)
                    geometry_node.location = (-600, 200)
                    separate_xyz_node.location = (-400, 200)
                    map_range_x.location = (-200, 300)
                    map_range_y.location = (-200, 200)
                    map_range_z.location = (-200, 100)
                    combine_xyz_node.location = (0, 200)
                    bsdf_node.location = (200, 200)
                    output_node.location = (400, 200)
                    
                    math_node_x = node_tree.nodes.new(type='ShaderNodeMath')
                    math_node_x.operation = 'SUBTRACT'
                    math_node_x.inputs[0].default_value = 1  # Set the first input value to 1
                    links.new(separate_xyz_node.outputs["X"], math_node_x.inputs[1])
                    
                    math_node_y = node_tree.nodes.new(type='ShaderNodeMath')
                    math_node_y.operation = 'SUBTRACT'
                    math_node_y.inputs[0].default_value = 1  # Set the first input value to 1
                    links.new(separate_xyz_node.outputs["Y"], math_node_y.inputs[1])
                    
                    math_node_z = node_tree.nodes.new(type='ShaderNodeMath')
                    math_node_z.operation = 'SUBTRACT'
                    math_node_z.inputs[0].default_value = 1  # Set the first input value to 1
                    links.new(separate_xyz_node.outputs["Z"], math_node_y.inputs[1])

                    # Defaults (axis)
                    in_forward_node = separate_xyz_node.outputs["Y"]
                    in_right_node = separate_xyz_node.outputs["X"]
                    in_up_node = separate_xyz_node.outputs["Z"]
                    
                    positionerrortext = "invalid axis setup, world normal mapping not valid"
                    # Link nodes
                    if bake_settings.forward_axis == 'POS_Y':
                        in_forward_node = separate_xyz_node.outputs["Y"]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = separate_xyz_node.outputs["X"]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = math_node_x.outputs[0]
                        
                        
                    elif bake_settings.forward_axis == 'NEG_Y':
                        in_forward_node = math_node_y.outputs[0]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = math_node_x.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = separate_xyz_node.outputs["X"]
                        
                    elif bake_settings.forward_axis == 'POS_X':
                        in_forward_node = separate_xyz_node.outputs["X"]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = math_node_y.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        
                    elif bake_settings.forward_axis == 'NEG_X':
                        in_forward_node = math_node_x.outputs[0]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = math_node_y.outputs[0]
                            
                    elif bake_settings.forward_axis == 'POS_Z':
                        in_forward_node = separate_xyz_node.outputs["Z"]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = math_node_x.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = separate_xyz_node.outputs["X"]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = math_node_y.outputs[0]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            print(positionerrortext)
                            
                    elif bake_settings.forward_axis == 'NEG_Z':
                        in_forward_node = math_node_z.outputs[0]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = separate_xyz_node.outputs["X"]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = math_node_x.outputs[0]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = math_node_y.outputs[0]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            print(positionerrortext)

                    # Link the nodes for world space normal mapping
                    links.new(geometry_node.outputs["Normal"], separate_xyz_node.inputs["Vector"])
                    links.new(in_right_node, map_range_x.inputs["Value"])
                    links.new(in_forward_node, map_range_y.inputs["Value"])
                    links.new(in_up_node, map_range_z.inputs["Value"])

                    # Configure Map Range nodes (from -1 to 1 mapped to 0 to 1)
                    for map_range in [map_range_x, map_range_y, map_range_z]:
                        map_range.inputs["From Min"].default_value = -1
                        map_range.inputs["From Max"].default_value = 1
                        map_range.inputs["To Min"].default_value = 0
                        map_range.inputs["To Max"].default_value = 1

                    # Link Map Range nodes to the Combine XYZ node
                    links.new(map_range_x.outputs["Result"], combine_xyz_node.inputs["X"])
                    links.new(map_range_y.outputs["Result"], combine_xyz_node.inputs["Y"])
                    links.new(map_range_z.outputs["Result"], combine_xyz_node.inputs["Z"])

                    # Link the combined result to the Base Color of the BSDF node
                    links.new(combine_xyz_node.outputs["Vector"], bsdf_node.inputs["Base Color"])

                    # Link the BSDF output to the Material Output node
                    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

                    # Apply axis remapping logic (ensure this function is defined to handle remapping)
#                    apply_axis_remap(separate_xyz_node, combine_xyz_node, forward_axis, up_axis, coord_system)

                    # Assign the temporary material to the object
                    user_obj.data.materials.clear()  # Clear any existing materials
                    user_obj.data.materials.append(wsn_material)
                    #
                    #
                    #
                    
                    
                    # Create an image for the curvature bake
                    img_name = f"{obj.name}_WORLD_SPACE_NORMAL"
                    img = bpy.data.images.new(name=img_name, width=bake_settings.resolution, height=bake_settings.resolution, float_buffer=True)
                    img.filepath_raw = CreateMapOutput(bake_type)
                    img.file_format = 'PNG'

                    # Assign the image to the bake
                    if bake_settings.selected_to_active == True:
                        img_node = img_nodes.new("ShaderNodeTexImage")
                    else:
                        img_node = nodes.new("ShaderNodeTexImage")
                    img_node.image = img
                    img_node.image.colorspace_settings.name = 'Non-Color'
                    nodes.active = img_node

                    # Bake the curvature as diffuse
                    bpy.context.scene.cycles.bake_type = 'DIFFUSE'
                    bpy.context.scene.render.bake.use_pass_direct = False
                    bpy.context.scene.render.bake.use_pass_indirect = False
                    bpy.ops.object.bake(type='DIFFUSE')

                    # Save and cleanup
                    img.save()
                    if bake_settings.selected_to_active == True:
                        img_nodes.remove(img_node)
                    else:
                        nodes.remove(img_node)
                    bpy.data.materials.remove(wsn_material)
                    bpy.data.images.remove(img)
                    
                    # Restore the original material
                    user_obj.data.materials[0] = original_material
                    bpy.context.scene.render.bake.use_pass_direct = bake_settings.direct
                    bpy.context.scene.render.bake.use_pass_indirect = bake_settings.indirect
                
                elif bake_type == "POSITION":
                    # Dictionary to store original data
                    normalize_to_unit_cube(obj)
                    
                    # Create a temporary position material
                    pos_material = bpy.data.materials.new(name="Temp_POS_Material")
                    pos_material.use_nodes = True
                    node_tree = pos_material.node_tree
                    nodes = pos_material.node_tree.nodes
                    links = pos_material.node_tree.links

                    # Remove default nodes for clarity
                    for node in nodes:
                        nodes.remove(node)

                    # Create necessary nodes
                    geometry_node = nodes.new("ShaderNodeNewGeometry")
                    separate_xyz_node = nodes.new("ShaderNodeSeparateXYZ")
                    combine_xyz_node = nodes.new("ShaderNodeCombineXYZ")
                    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
                    output_node = nodes.new("ShaderNodeOutputMaterial")

                    # Position nodes for better layout visualization (optional)
                    geometry_node.location = (-400, 200)
                    separate_xyz_node.location = (-200, 200)
                    combine_xyz_node.location = (0, 200)
                    bsdf_node.location = (200, 200)
                    output_node.location = (400, 200)
                    
                    #
                    #
                    #
                    #

                    math_node_x = node_tree.nodes.new(type='ShaderNodeMath')
                    math_node_x.operation = 'SUBTRACT'
                    math_node_x.inputs[0].default_value = 1  # Set the first input value to 1
                    links.new(separate_xyz_node.outputs["X"], math_node_x.inputs[1])
                    
                    math_node_y = node_tree.nodes.new(type='ShaderNodeMath')
                    math_node_y.operation = 'SUBTRACT'
                    math_node_y.inputs[0].default_value = 1  # Set the first input value to 1
                    links.new(separate_xyz_node.outputs["Y"], math_node_y.inputs[1])
                    
                    math_node_z = node_tree.nodes.new(type='ShaderNodeMath')
                    math_node_z.operation = 'SUBTRACT'
                    math_node_z.inputs[0].default_value = 1  # Set the first input value to 1
                    links.new(separate_xyz_node.outputs["Z"], math_node_y.inputs[1])

                    # Defaults (axis)
                    in_forward_node = separate_xyz_node.outputs["Y"]
                    in_right_node = separate_xyz_node.outputs["X"]
                    in_up_node = separate_xyz_node.outputs["Z"]
                    
                    positionerrortext = "invalid axis setup, position mapping not valid"
                    # Link nodes
                    if bake_settings.forward_axis == 'POS_Y':
                        in_forward_node = separate_xyz_node.outputs["Y"]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = separate_xyz_node.outputs["X"]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = math_node_x.outputs[0]
                        
                        
                    elif bake_settings.forward_axis == 'NEG_Y':
                        in_forward_node = math_node_y.outputs[0]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = math_node_x.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = separate_xyz_node.outputs["X"]
                        
                    elif bake_settings.forward_axis == 'POS_X':
                        in_forward_node = separate_xyz_node.outputs["X"]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = math_node_y.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        
                    elif bake_settings.forward_axis == 'NEG_X':
                        in_forward_node = math_node_x.outputs[0]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = separate_xyz_node.outputs["Z"]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = math_node_z.outputs[0]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            in_right_node = math_node_y.outputs[0]
                            
                    elif bake_settings.forward_axis == 'POS_Z':
                        in_forward_node = separate_xyz_node.outputs["Z"]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = math_node_x.outputs[0]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = separate_xyz_node.outputs["X"]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = math_node_y.outputs[0]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            print(positionerrortext)
                            
                    elif bake_settings.forward_axis == 'NEG_Z':
                        in_forward_node = math_node_z.outputs[0]
                        if bake_settings.up_axis == 'POS_Y':
                            in_up_node = separate_xyz_node.outputs["Y"]
                            in_right_node = separate_xyz_node.outputs["X"]
                        elif bake_settings.up_axis == 'NEG_Y':
                            in_up_node = math_node_y.outputs[0]
                            in_right_node = math_node_x.outputs[0]
                        elif bake_settings.up_axis == 'POS_X':
                            in_up_node = separate_xyz_node.outputs["X"]
                            in_right_node = math_node_y.outputs[0]
                        elif bake_settings.up_axis == 'NEG_X':
                            in_up_node = math_node_x.outputs[0]
                            in_right_node = separate_xyz_node.outputs["Y"]
                        elif bake_settings.up_axis == 'POS_Z':
                            in_up_node = separate_xyz_node.outputs["Z"]
                            print(positionerrortext)
                        elif bake_settings.up_axis == 'NEG_Z':
                            in_up_node = math_node_z.outputs[0]
                            print(positionerrortext)
                        
                    
                    links.new(geometry_node.outputs["Position"], separate_xyz_node.inputs["Vector"])
                    links.new(in_right_node, combine_xyz_node.inputs["X"])
                    links.new(in_forward_node, combine_xyz_node.inputs["Y"])
                    links.new(in_up_node, combine_xyz_node.inputs["Z"])
                    
                    links.new(combine_xyz_node.outputs["Vector"], bsdf_node.inputs["Base Color"])
                    links.new(bsdf_node.outputs["BSDF"], output_node.inputs["Surface"])

                    # Apply the axis remapping logic (this function should be implemented to handle the actual remapping)
#                    apply_axis_remap(separate_xyz_node, combine_xyz_node, forward_axis, up_axis, coord_system)

                    # Assign the temporary material
                    obj.data.materials.clear()
                    obj.data.materials.append(pos_material)
                    
                    # Create an image for the position bake
                    img_name = f"{obj.name}_POSITION"
                    img = bpy.data.images.new(name=img_name, width=bake_settings.resolution, height=bake_settings.resolution, float_buffer=True)
                    img.filepath_raw = CreateMapOutput(bake_type)
                    img.file_format = 'PNG'

                    # Assign the image to the bake
                    img_node = nodes.new("ShaderNodeTexImage")
                    img_node.image = img
                    img_node.image.colorspace_settings.name = 'Non-Color'
                    nodes.active = img_node

                    # Bake the position as diffuse
                    if non_active_obj != None:
                        non_active_obj.hide_render = True
                        scene.render.bake.use_selected_to_active = False
                        bpy.ops.object.select_all(action='DESELECT')
                        bpy.context.view_layer.objects.active = obj
                        obj.select_set(True)
                    
                    bpy.context.scene.cycles.bake_type = 'DIFFUSE'
                    bpy.context.scene.render.bake.use_pass_direct = False
                    bpy.context.scene.render.bake.use_pass_indirect = False
                    bpy.ops.object.bake(type='DIFFUSE')
                    
                    
                    # Save and cleanup
                    img.save()
                    bpy.data.images.remove(img)
                    nodes.remove(img_node)
                    bpy.data.materials.remove(pos_material)
                    revert_normalization(obj)
                    
                    # Restore the original material
                    obj.data.materials[0] = original_material
                    if non_active_obj != None:
                        non_active_obj.select_set(True)
                        non_active_obj.hide_render = False
                        
                    bpy.context.scene.render.bake.use_pass_direct = bake_settings.direct
                    bpy.context.scene.render.bake.use_pass_indirect = bake_settings.indirect
                    scene.render.bake.use_selected_to_active = bake_settings.selected_to_active
                    
                
                else:
                    # For other bake types
                    img_name = f"{obj.name}_{bake_type}"
                    img = bpy.data.images.new(name=img_name, width=bake_settings.resolution, height=bake_settings.resolution, float_buffer=True)
                    img.filepath_raw = CreateMapOutput(bake_type)
                    img.file_format = 'PNG'
                    
                    # Add image node to material
                    mat.use_nodes = True
                    nodes = mat.node_tree.nodes
                    img_node = nodes.new(type="ShaderNodeTexImage")
                    img_node.image = img
                    img_node.image.colorspace_settings.name = 'Non-Color'
                    
                    img_node.name = bake_type

                    # Set image as active for baking
                    bpy.context.scene.cycles.bake_type = bake_type
                    bpy.context.view_layer.objects.active = obj
                    nodes.active = img_node
                    
                    # Perform the bake
                    if bake_type == 'NORMAL':
                        if bake_settings.normal_format == 'DIRECTX':
                            scene.render.bake.normal_g = 'NEG_Y'
                        else:
                            scene.render.bake.normal_g = 'POS_Y'

                    bpy.ops.object.bake(type=bake_type)
                    
                    # Save the image
                    img.save()
                    bpy.data.images.remove(img)
                    nodes.remove(img_node)
                    
                    #Legacy normal conversion
#                    if bake_type == 'NORMAL':
#                        if bake_settings.normal_format == 'DIRECTX':
#                            process_directx_normal(img.filepath_raw)
##                            bpy.app.timers.register(lambda: delayed_process_directx(img.filepath_raw))
#                            self.report({'INFO'}, "Processing DirectX normal conversion")
                            
        
        if not islitmap:
            if not copydestroyed:
                if sourceref != None:
                    bpy.data.objects.remove(sourceref)
                if targetref != None:
                    bpy.data.objects.remove(targetref)
                bake_settings.source_object.hide_render = False
                bake_settings.target_object.hide_render = False
        
        purge_unused_data()
        self.report({'INFO'}, "Baking complete")
        
        # reset the scene
        bpy.context.scene.render.engine = default_engine
        
        return {'FINISHED'}

original_data = {}
update_bake_margin 

def purge_unused_data():
    for data_type in [bpy.data.meshes, bpy.data.materials, bpy.data.textures, bpy.data.images, bpy.data.curves]:
        for block in data_type:
            if block.users == 0:
                data_type.remove(block)
                
def delayed_process_directx(image_filepath):
    if bpy.ops.object.bake.poll():
        process_directx_normal(image_filepath)
        return None  # Stops the timer
    return 0.5  # Check again in 0.5 seconds

def register():
    bpy.utils.register_class(SmartBakingPanel)
    bpy.utils.register_class(OpenOrCreateFolderOperator)
    bpy.utils.register_class(BakeSettings)
    bpy.utils.register_class(BakeSenseOutput)
    bpy.utils.register_class(BakeSelectedMapsOperator)
    bpy.app.handlers.load_post.append(update_bake_margin)
    
    bpy.types.Scene.folder_path = bpy.props.StringProperty(
        name="Folder Path",
        description="Absolute path to open or create",
        default="",
        subtype='DIR_PATH'
    )
    
    bpy.types.Scene.smart_bake_settings = bpy.props.PointerProperty(type=BakeSettings)

def unregister():
    bpy.utils.unregister_class(SmartBakingPanel)
    bpy.utils.unregister_class(OpenOrCreateFolderOperator)
    bpy.utils.unregister_class(BakeSettings)
    bpy.utils.unregister_class(BakeSenseOutput)
    bpy.utils.unregister_class(BakeSelectedMapsOperator)
    bpy.app.handlers.load_post.remove(update_bake_margin)
    
    del bpy.types.Scene.folder_path
    
    del bpy.types.Scene.smart_bake_settings

if __name__ == "__main__":
    register()
