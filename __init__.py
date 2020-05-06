import bpy
from bpy_extras.io_utils import orientation_helper, ImportHelper, axis_conversion
from bpy.props import BoolProperty, FloatProperty, StringProperty

bl_info = {
    "name": "The Witcher .mdb (.mba) importer",
    "author": "nk2",
    "blender": (2, 82, 0),
    "location": "File > Import",
    "description": "Import .mdb and .mba as mesh with animations",
    "warning": "",
    "wiki_url": "ololol",
    "support": 'TESTING',
    "category": "Import-Export"
}

@orientation_helper(axis_forward='Y', axis_up='Z')
class ImportMDB(bpy.types.Operator, ImportHelper):
    """Import from MDB file format (.mdb, .mba)"""
    bl_idname = "import_scene.thewitcher_mdb"
    bl_label = 'Import MDB'
    bl_options = {'UNDO'}

    filename_ext = ".mdb;.mba"
    filter_glob: StringProperty(default="*.mdb;*.mba", options={'HIDDEN'})

    base_path: StringProperty(
        name="Extracted BIF base path",
        description="The Wither extracted .bif path (contains textures00/ meshes00/)",
        default="../",
    )

    def execute(self, context):
        import importlib, sys  # required

        # reloads class' parent module and returns updated class
        def reload_class(c):
            mod = sys.modules.get(c.__module__)
            importlib.reload(mod)
            return mod.__dict__[c.__name__]

        # imports to be updated
        from . import import_mdb

        importlib.reload(import_mdb)  # reload imported module

        keywords = self.as_keywords(
            ignore=(
                "axis_forward",
                "axis_up",
                "filter_glob",
            )
        )

        global_matrix = axis_conversion(from_forward=self.axis_forward, from_up=self.axis_up).to_4x4()
        keywords["global_matrix"] = global_matrix

        return import_mdb.load(self, context, **keywords)

addon_keymaps = []

classes = (
    ImportMDB,
)


def menu_func_import(self, context):
    self.layout.operator(ImportMDB.bl_idname, text="The Witcher (.mdb, .mba)")


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

    # handle the keymap
    wm = bpy.context.window_manager

    if wm.keyconfigs.addon:
        km = wm.keyconfigs.addon.keymaps.new(name="Window", space_type='EMPTY')
        kmi = km.keymap_items.new(ImportMDB.bl_idname, 'F', 'PRESS', ctrl=True, shift=True)
        addon_keymaps.append((km, kmi))


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    # handle the keymap
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    del addon_keymaps[:]


if __name__ == "__main__":
    register()
