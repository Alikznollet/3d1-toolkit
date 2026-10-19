# Module imports.
if "bpy" in locals():
    import importlib
    importlib.reload(pre_flight)
    importlib.reload(blueprints)
else:
    from .modules import pre_flight
    from .modules import blueprints

import bpy

addon_keymaps = []

def register():
    # Register the sub-modules
    pre_flight.register()
    blueprints.register()
    
    # Set up all hotkeys centrally
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        
        # Validation Hotkey (Ctrl + Shift + V)
        kmi_validate = km.keymap_items.new("dae.run_pre_flight", type="V", value="PRESS", ctrl=True, shift=True)
        addon_keymaps.append((km, kmi_validate))
        
        # Blueprint Hotkey (Ctrl + Shift + B)
        kmi_blueprint = km.keymap_items.new("dae.import_blueprints", type="B", value="PRESS", ctrl=True, shift=True)
        addon_keymaps.append((km, kmi_blueprint))

def unregister():
    # Remove hotkeys
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for km, kmi in addon_keymaps:
            km.keymap_items.remove(kmi)
    addon_keymaps.clear()
    
    # Unregister the sub-modules
    pre_flight.unregister()
    blueprints.unregister()

if __name__ == "__main__":
    register()
