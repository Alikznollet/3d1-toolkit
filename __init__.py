import bpy
from bpy.app.handlers import persistent

phantasm_cache = {
  "bad_meshes": [],
  "bad_materials": []
}

@persistent
def phantasm_live_check(check, depsgraph):
  if depsgraph.id_type_updated("OBJECT") or depsgraph.id_type_updated("MATERIAL"):
    phantasm_cache["bad_meshes"].clear()
    phantasm_cache["bad_materials"].clear()

    # Scan for bad meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and not obj.name.startswith("SM_"):
            phantasm_cache["bad_meshes"].append(obj.name)

    # Scan for bad materials
    for mat in bpy.data.materials:
        if not mat.name.startswith("M_") and not mat.name.startswith("Dots"):
            phantasm_cache["bad_materials"].append(mat.name)

    # Force the UI to refresh immediately
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()

class PHANTASM_PT_MainPanel(bpy.types.Panel):
  bl_space_type = "VIEW_3D"
  bl_region_type = "UI"
  bl_category = "Phantasm"
  bl_label = "Asset validation"

  def draw(self, context):
    layout = self.layout
    
    # Read from our cache
    bad_meshes = phantasm_cache["bad_meshes"]
    bad_mats = phantasm_cache["bad_materials"]
    
    # Mesh UI
    mesh_box = layout.box()
    mesh_box.label(text="Invalid Meshes:", icon='MESH_DATA')
    if not bad_meshes:
        mesh_box.label(text="All Good!", icon='CHECKMARK')
    else:
        for name in bad_meshes:
            mesh_box.label(text=name, icon='CANCEL')

    # Material UI
    mat_box = layout.box()
    mat_box.label(text="Invalid Materials:", icon='MATERIAL')
    if not bad_mats:
        mat_box.label(text="All Good!", icon='CHECKMARK')
    else:
        for name in bad_mats:
            mat_box.label(text=name, icon='CANCEL')

classes = (
  PHANTASM_PT_MainPanel,
)

def register():
  print("Phantasm has been loaded into Blender.")
  for cls in classes:
    bpy.utils.register_class(cls)

  if phantasm_live_check not in bpy.app.handlers.depsgraph_update_post:
    bpy.app.handlers.depsgraph_update_post.append(phantasm_live_check)

def unregister():
  print("Phantasm has been unloaded from Blender.")
  for cls in classes:
    bpy.utils.unregister_class(cls)

  if phantasm_live_check in bpy.app.handlers.depsgraph_update_post:
      bpy.app.handlers.depsgraph_update_post.remove(phantasm_live_check)
