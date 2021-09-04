import bpy
import bmesh
from mathutils import Vector
from bpy.props import (
    StringProperty,
    BoolProperty,
    BoolVectorProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
)

from bl_ui.properties_paint_common import UnifiedPaintPanel

import os
import sys
import ensurepip
import subprocess
import importlib
from collections import namedtuple


# Install and import dependencies
from .import_utils import import_dependencies, Dependency
dependencies = [
    Dependency('opencv-python', 'cv2', 'cv'),
]
import_dependencies(dependencies, globals())

import numpy as np

from .sampling import sample_uv
from .utils import color_dist, get_ndarray


bl_info = {
    'name': 'Separate By Color',
    'author': 'jd3',
    'version': (0, 0),
    'blender': (2, 90, 0),
    'category': 'Object',
}   

PALETTE_ID = 'separate_by_color_palette'
BAKE_IMAGE_NAME = 'separate_by_color_tmp_bake'

BAKE_TYPE_OPTIONS = ['NORMAL', 'COMBINED', 'DIFFUSE', 'GLOSSY', 'TRANSMISSION']
BAKE_TYPE_ITEMS = [
    ('NORMAL', 'Normal', '', 1),
    ('COMBINED', 'Combined', '', 2),
    ('DIFFUSE', 'Diffuse', '', 3),
    ('GLOSSY', 'Glossy', '', 4),
    ('TRANSMISSION', 'Transmission', '', 5),
]

PASS_use_pass_OPTIONS = {'AO', 'EMIT', 'DIRECT', 'INDIRECT', 'COLOR',
                         'DIFFUSE', 'GLOSSY', 'TRANSMISSION'}


def get_paint_settings(context):
    return context.tool_settings.image_paint


class SeparateByColor(bpy.types.Operator):
    '''
    Separate an object into multiple objects by color of each face.
    '''
    bl_idname = 'object.separate_by_color'
    bl_label = 'Separate By Color'
    bl_options = {'REGISTER', 'UNDO'}

    bake_type: EnumProperty(items=BAKE_TYPE_ITEMS, name='Bake Type', default='COMBINED')

    # Lighting
    use_pass_direct: BoolProperty(name='Direct', default=False)
    use_pass_indirect: BoolProperty(name='Indirect', default=False)

    # Contributions
    use_pass_ao: BoolProperty(name='AO', default=False)
    use_pass_emit: BoolProperty(name='Emit', default=True)
    use_pass_color: BoolProperty(name='Color', default=False)
    use_pass_defuse: BoolProperty(name='Defuse', default=False)
    use_pass_glossy: BoolProperty(name='Glossy', default=False)
    use_pass_transmission: BoolProperty(name='Transmission', default=False)

    # Texture settings
    bake_texture_width: IntProperty(name='Bake Texture Width', default=512)
    bake_texture_height: IntProperty(name='Bake Texture Height', default=512)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if obj is None:
            return False
        if obj.data is None:
            return False
        return True

    def execute(self, context):
        print('execute()')
        paint_settings = get_paint_settings(context)
        palette_colors = np.array([c.color for c in paint_settings.palette.colors])
        n_colors = len(palette_colors)

        print(palette_colors)

        # add alpha channal
        palette_colors = np.append(palette_colors, np.ones((n_colors, 1)), axis=1)

        bpy.ops.object.mode_set(mode='OBJECT')
        obj = context.active_object
        mesh = obj.data

        mat = obj.material_slots[0].material
        nodes = mat.node_tree.nodes
        node = nodes.new('ShaderNodeTexImage')
        if BAKE_IMAGE_NAME in bpy.data.images:
            image = bpy.data.images[BAKE_IMAGE_NAME]
        else:
            image = bpy.data.images.new(BAKE_IMAGE_NAME, self.bake_texture_width, self.bake_texture_height)
        node.image = image
        nodes.active = node

        pass_filter = set()
        if self.use_pass_direct:
            pass_filter.add('DIRECT')
        if self.use_pass_indirect:
            pass_filter.add('INDIRECT')
        if self.use_pass_ao:
            pass_filter.add('AO')
        if self.use_pass_emit:
            pass_filter.add('EMIT')
        if self.use_pass_color:
            pass_filter.add('COLOR')
        if self.use_pass_defuse:
            pass_filter.add('DIFFUSE')
        if self.use_pass_glossy:
            pass_filter.add('GLOSSY')
        if self.use_pass_transmission:
            pass_filter.add('TRANSMISSION')

        bpy.ops.object.bake(type=self.bake_type, pass_filter=pass_filter, use_clear=True)

        bpy.ops.object.mode_set(mode='EDIT')

        bm = bmesh.from_edit_mesh(mesh)
        uv_layer = bm.loops.layers.uv.active

        image_data = get_ndarray(image)

        for i in range(n_colors):
            bpy.ops.mesh.select_all(action='DESELECT')
            bm.faces.ensure_lookup_table()

            faces_colors = []
            for face in bm.faces:
                center = Vector((0, 0))
                for loop in face.loops:
                    uv = loop[uv_layer].uv
                    center += uv
                center /= len(face.loops)
                color = sample_uv(image_data, center)
                faces_colors.append(color)
            faces_colors = np.array(faces_colors)

            distances = np.zeros((len(bm.faces), n_colors))
            for j in range(n_colors):
                distances[:, j] = color_dist(faces_colors, palette_colors[j])

            nearest_color_index = np.argmin(distances, axis=1)
            for j, face in enumerate(bm.faces):
                if nearest_color_index[j] == i:
                    face.select = True

            bm.select_flush(True)
            try:
                bpy.ops.mesh.separate(type='SELECTED')
            except RuntimeError as e:
                if 'Nothing selected' in str(e):
                    print(f'skip color: {palette_colors[i]}')
                    continue
                else:
                    print(f'error: \"{str(e)}\"')
            bmesh.update_edit_mesh(mesh, True)

            if len(bm.faces) == 0:
                break

        # clear tmp data
        # mat.node_tree.nodes.remove(node)
        # bpy.data.images.remove(image)
        bpy.ops.object.mode_set(mode='OBJECT')

        return {'FINISHED'}

    def draw(self, context):
        self.__class__.draw_parameters(self.layout, self, context)

    @staticmethod
    def draw_parameters(layout, op_instance, context):

        r0 = layout.row()
        r0.label(text='Bake Type')
        r0.prop(op_instance, 'bake_type', text="")

        r1 = layout.row()
        r1c1 = r1.column()
        r1c1.label(text='Lighting')
        r1c2 = r1.column()
        r1c2.prop(op_instance, 'use_pass_direct')
        r1c2.prop(op_instance, 'use_pass_indirect')

        r2 = layout.row()
        r2c1 = r2.column()
        r2c1.label(text='Contributions')
        r2c2 = r2.column()
        r2c2.prop(op_instance, 'use_pass_ao')
        r2c2.prop(op_instance, 'use_pass_emit')
        r2c2.prop(op_instance, 'use_pass_color')
        r2c2.prop(op_instance, 'use_pass_defuse')
        r2c2.prop(op_instance, 'use_pass_glossy')
        r2c2.prop(op_instance, 'use_pass_transmission')

        layout.label(text='Texture resolution')
        r3 = layout.row()
        r3.prop(op_instance, 'bake_texture_width', text='Width')
        r3.prop(op_instance, 'bake_texture_height', text='Height')


kmi = None


class SeparateByColorPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Dev'
    bl_idname = 'OBJECT_PT_separate_by_color'
    bl_label = 'Separate By Color'

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw(self, context):
        layout = self.layout

        c1 = layout.column()
        SeparateByColor.draw_parameters(c1, kmi.properties, context)
        op = c1.operator('object.separate_by_color', text='Separate by Color')
        op.use_pass_direct = kmi.properties.use_pass_direct
        op.use_pass_indirect = kmi.properties.use_pass_indirect
        op.use_pass_ao = kmi.properties.use_pass_ao
        op.use_pass_emit = kmi.properties.use_pass_emit
        op.use_pass_color = kmi.properties.use_pass_color
        op.use_pass_defuse = kmi.properties.use_pass_defuse
        op.use_pass_glossy = kmi.properties.use_pass_glossy
        op.use_pass_transmission = kmi.properties.use_pass_transmission

        c2 = layout.column()
        c2.label(text='Palette')
        paint_settings = get_paint_settings(context)
        brush = paint_settings.brush
        UnifiedPaintPanel.prop_unified_color_picker(c2, context, brush, 'color', value_slider=True)
        UnifiedPaintPanel.prop_unified_color(c2, context, brush, 'color', text='')

        # c2.template_ID(context.scene, PALETTE_ID, new='palette.new')
        # c2.template_palette(context.scene, PALETTE_ID, color=True)
        c2.template_ID(paint_settings, 'palette', new='palette.new')
        if paint_settings.palette:
            layout.template_palette(paint_settings, "palette", color=True)


def set_keymap():
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name='3D View', space_type='EMPTY')
    global kmi
    kmi = km.keymap_items.new('object.separate_by_color', 'NONE', 'ANY')


classes = [
    SeparateByColor,
    SeparateByColorPanel,
]




def register():
    print('Register')

    # bpy.types.Scene.separate_by_color_palette = PointerProperty(name='Palette', type=bpy.types.Palette)

    for cls in classes:
        bpy.utils.register_class(cls)

    set_keymap()


def unregister():
    print('Unregister')
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
