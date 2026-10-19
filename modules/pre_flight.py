import bpy
import bmesh

KEYS: list[str] = [
	"naming",
	"materials",
	"ngons",
	"non-manifolds",
	"overlapping",
	"modifiers",
	"unused_mats",
	"unused_images",
	"psd_images",
]

# Whether the checks have been ran once before.
ran_once: bool = False
report_cache = {} # Dynamic dict of values

class DAE_OT_RunChecks(bpy.types.Operator):
	bl_idname = "dae.run_pre_flight"
	bl_label = "Run Pre-Flight Checks"
	bl_description = "Scans the entire scene for assignment requirements."

	def execute(self, context): 
		global ran_once
		ran_once = True

		# Clear and initialize the cache
		for key in KEYS:
			if key not in report_cache:
				report_cache[key] = []
			report_cache[key].clear()

		# Scan Objects
		for obj in bpy.context.scene.objects:
			if obj.type == "MESH":
				# Check the Prefix
				if not obj.name.startswith("SM_"):
					report_cache["naming"].append(obj.name)

				# Check if there are any modifiers still not applied.
				if len(obj.modifiers) > 0:
					report_cache["modifiers"].append(obj.name)

				# We'll copy the mesh.
				bm = bmesh.new()
				bm.from_mesh(obj.data)

				# Check for n-gons too.
				if any(len(p.vertices) > 4 for p in obj.data.polygons):
					report_cache["ngons"].append(obj.name)

				# Check for non-manifolds.
				for edge in bm.edges:
					# Flag edges that have no faces or more than 2.
					if not edge.is_manifold and not edge.is_boundary:
						report_cache["non-manifolds"].append(obj.name)
						break

				# Check for overlapping edges.
				original_vert_count = len(bm.verts)

				# Run a merge by distance on the copied mesh.
				bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

				# If the count went down there's overlapping vertices.
				if len(bm.verts) < original_vert_count:
					report_cache["overlapping"].append(obj.name)

				# Delete the bmesh
				bm.free()

		# Scan Materials
		for mat in bpy.data.materials:
			# Check for material naming.
			if not mat.name.startswith("M_") and not mat.name.startswith("Dots"):
				report_cache["materials"].append(mat.name)

			# Check if the material even has users.
			if mat.users == 0:
				report_cache["unused_mats"].append(mat.name)

		# Scan the textures/images
		for img in bpy.data.images:
			# Ignore blender internals
			if img.type != "IMAGE" or img.source != "FILE":
				continue

			# Check for unused ones.
			if img.users == 0:
				report_cache["unused_images"].append(img.name)

			# Check for psd format
			filepath = img.filepath.lower()
			if filepath.endswith(".psd") or img.name.lower().endswith(".psd"):
				report_cache["psd_images"].append(img.name)

		# Redraw UI
		for area in context.screen.areas:
			if area.type == "VIEW_3D":
				area.tag_redraw()

		bpy.ops.dae.pre_flight_popup("INVOKE_DEFAULT")

		return {"FINISHED"}

class DAE_OT_SelectAsset(bpy.types.Operator):
	bl_idname = "dae.select_asset"
	bl_label = "Select Asset"

	asset_name: bpy.props.StringProperty()

	def execute(self, context):
		if context.active_object and context.active_object.mode != "OBJECT":
			bpy.ops.object.mode_set(mode="OBJECT")

		# Deselect all previous objects
		bpy.ops.object.select_all(action="DESELECT")

		# Select the object if one exists.
		obj = bpy.data.objects.get(self.asset_name)
		if obj:
			obj.select_set(True)
			context.view_layer.objects.active = obj
		else:
			self.report({"ERROR"}, "Object no longer exists. Try re-running check.")
			return {"CANCELLED"}

		return {"FINISHED"}

class DAE_OT_SelectMaterial(bpy.types.Operator):
	bl_idname = "dae.select_material"
	bl_label = "Find Material"

	mat_name: bpy.props.StringProperty()

	def execute(self, context):
		target_mat = bpy.data.materials.get(self.mat_name)
		if not target_mat: 
			self.report({"ERROR"}, "Material no longer exists. Try re-running check.")
			return {"CANCELLED"}

		found_objects = []
		active_obj = None
		active_slot_index = 0

		for obj in bpy.context.scene.objects:
			if obj.type == "MESH":
				for i, slot in enumerate(obj.material_slots):
					if slot.material == target_mat:
						found_objects.append(obj)

						# Make the first one active
						if not active_obj:
							active_obj = obj
							active_slot_index = i

						break

		if found_objects:
			# Go to object mode
			if context.active_object and context.active_object.mode != 'OBJECT':
				bpy.ops.object.mode_set(mode='OBJECT')
			bpy.ops.object.select_all(action='DESELECT')

			# Select all objects we found.
			for obj in found_objects:
				obj.select_set(True)

			# Make the first one active.
			context.view_layer.objects.active = active_obj
			active_obj.active_material_index = active_slot_index

			self.report({"INFO"}, f"Selected {len(found_objects)} objects using material '{self.mat_name}'.")
		else:
			self.report({"WARNING"}, f"Material '{self.mat_name}' had 0 users.")

		return {"FINISHED"}

class DAE_OT_PreFlightPopup(bpy.types.Operator):
	bl_idname = "dae.pre_flight_popup"
	bl_label = "DAE 3D1 Validation"
	
	def invoke(self, context, event):
		return context.window_manager.invoke_popup(self, width=280)
		
	def execute(self, context):
		return {'FINISHED'}
	
	def draw(self, context):
		layout = self.layout
		layout.label(text="Is your asset ready?")
		
		if all(not report_cache[key] for key in KEYS):
			box = layout.box()
			box.label(text="Yes it is! Time to export!", icon='CHECKMARK')
			return

		#
		# NAMING
		#

		# Add a label for naming issues.
		if report_cache.get("naming") or report_cache.get("materials"):
			layout.separator()
			layout.label(text="Naming Issues:", icon='INFO')
			
		# Display Mesh Name Errors
		if report_cache["naming"]:
			box = layout.box()
			box.label(text="Missing 'SM_' Prefix:", icon='ERROR')
			col = box.column(align=True)
			for n in report_cache["naming"]: 
				col.operator("dae.select_asset", text=n, icon='OUTLINER_OB_MESH').asset_name = n

		# Display Material Errors
		if report_cache["materials"]:
			box = layout.box()
			box.label(text="Missing 'M_' Prefix:", icon='ERROR')
			col = box.column(align=True)
			for m in report_cache["materials"]: 
				col.operator("dae.select_material", text=m, icon='MATERIAL').mat_name = m

		#
		# MESHES
		#

		# Add a label for mesh issues.
		if report_cache.get("modifiers") or report_cache.get("ngons") or report_cache.get("non-manifolds") or report_cache.get("overlapping"):
			layout.separator()
			layout.label(text="Mesh Issues:", icon='INFO')

		# Display unapplied modifiers
		if report_cache["modifiers"]:
			box = layout.box()
			box.label(text="Unapplied Modifiers:", icon='ERROR')
			col = box.column(align=True)
			for m in report_cache["modifiers"]: 
				col.operator("dae.select_asset", text=m, icon='MODIFIER_DATA').asset_name = m
				
		# Display N-Gon Errors
		if report_cache["ngons"]:
			box = layout.box()
			box.label(text="Contains N-Gons:", icon='ERROR')
			col = box.column(align=True)
			for g in report_cache["ngons"]: 
				col.operator("dae.select_asset", text=g, icon='MESH_DATA').asset_name = g

		# Display Non-Manifolds Errors
		if report_cache["non-manifolds"]:
			box = layout.box()
			box.label(text="Contains Non-Manifolds:", icon='ERROR')
			col = box.column(align=True)
			for nm in report_cache["non-manifolds"]: 
				col.operator("dae.select_asset", text=nm, icon='MOD_WIREFRAME').asset_name = nm

		# Display Overlapping Geometry Errors
		if report_cache["overlapping"]:
			box = layout.box()
			box.label(text="Overlapping Verts/Faces:", icon='ERROR')
			col = box.column(align=True)
			for ov in report_cache["overlapping"]: 
				col.operator("dae.select_asset", text=ov, icon='UV_VERTEX').asset_name = ov

		#
		# Data cleanup
		#

		# --- Data Cleanup Section ---
		if report_cache.get("unused_mats") or report_cache.get("unused_images") or report_cache.get("psd_images"):
			layout.separator()
			layout.label(text="Clean Up Your Data:", icon='ORPHAN_DATA')

		# Unused Materials
		if report_cache.get("unused_mats"):
			box = layout.box()
			box.label(text="Unused Materials:", icon='TRASH')
			col = box.column(align=True)
			for um in report_cache["unused_mats"]:
				col.label(text=um, icon='MATERIAL')

		# Unused Textures
		if report_cache.get("unused_images"):
			box = layout.box()
			box.label(text="Unused Textures:", icon='TRASH')
			col = box.column(align=True)
			for ui in report_cache["unused_images"]:
				col.label(text=ui, icon='IMAGE_DATA')

		# PSD Files Still in Use
		if report_cache.get("psd_images"):
			box = layout.box()
			box.label(text="PSD Textures Found:", icon='CANCEL')
			col = box.column(align=True)
			for psd in report_cache["psd_images"]:
				col.label(text=psd, icon='FILE_IMAGE')

classes = (
    DAE_OT_RunChecks,
    DAE_OT_SelectAsset,
    DAE_OT_SelectMaterial,
    DAE_OT_PreFlightPopup,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
				
