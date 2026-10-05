import bpy
import bmesh
import bpy.props

report_cache = {
  "ran_once": False,
	"naming": [],
	"materials": [],
	"ngons": [],
	"non-manifolds": [],
	"overlapping": [],
}

class DAE_OT_RunChecks(bpy.types.Operator):
	bl_idname = "dae.run_pre_flight"
	bl_label = "Run Pre-Flight Checks"
	bl_description = "Scans the entire scene for assignment requirements."

	def execute(self, context): 
		report_cache["ran_once"] = True
		
		# Clear the cache
		report_cache["naming"].clear()
		report_cache["materials"].clear()
		report_cache["ngons"].clear()
		report_cache["non-manifolds"].clear()
		report_cache["overlapping"].clear()

		# Scan Objects
		for obj in bpy.context.scene.objects:
			if obj.type == "MESH":
				# Check the Prefix
				if not obj.name.startswith("SM_"):
					report_cache["naming"].append(obj.name)

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
			if not mat.name.startswith("M_") and not mat.name.startswith("Dots"):
				report_cache["materials"].append(mat.name)

		# Redraw UI
		for area in context.screen.areas:
			if area.type == "VIEW_3D":
				area.tag_redraw()

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

# 3. THE UI PANEL
class DAE_PT_PreFlightPanel(bpy.types.Panel):
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Pre-Flight'
	bl_label = "DAE 3D1 Validation"
	
	def draw(self, context):
		layout = self.layout
		
		# The Main Button
		layout.operator("dae.run_pre_flight", text="Run All Checks", icon='PLAY')
		
		# Only show results if the button has been clicked at least once
		if report_cache["ran_once"]:
			layout.separator()
			
			# Check if all lists are empty (meaning everything passed)
			if not report_cache["naming"] and not report_cache["materials"] and not report_cache["ngons"]:
				layout.label(text="Scene Passed! Ready for export.", icon='FILE_TICK')
				return
					
			# Display Mesh Name Errors
			if report_cache["naming"]:
				box = layout.box()
				box.label(text="Missing 'SM_' Prefix:", icon='ERROR')
				for n in report_cache["naming"]: 
					box.operator("dae.select_asset", text=n, icon='VIEWZOOM').asset_name = n
					
			# Display Material Errors
			if report_cache["materials"]:
				box = layout.box()
				box.label(text="Missing 'M_' Prefix:", icon='ERROR')
				for m in report_cache["materials"]: 
					box.operator("dae.select_material", text=m, icon='VIEWZOOM').mat_name = m
					
			# Display N-Gon Errors
			if report_cache["ngons"]:
				box = layout.box()
				box.label(text="Contains N-Gons:", icon='ERROR')
				for g in report_cache["ngons"]: 
					box.operator("dae.select_asset", text=g, icon='VIEWZOOM').asset_name = g

			# Display Non-Manifolds Errors
			if report_cache["non-manifolds"]:
				box = layout.box()
				box.label(text="Contains Non-Manifolds:", icon='ERROR')
				for nm in report_cache["non-manifolds"]: 
					box.operator("dae.select_asset", text=nm, icon='VIEWZOOM').asset_name = nm

			# Display Overlapping Geometry Errors
			if report_cache["overlapping"]:
				box = layout.box()
				box.label(text="Overlapping Verts/Faces:", icon='ERROR')
				for ov in report_cache["overlapping"]: 
					box.operator("dae.select_asset", text=ov, icon='VIEWZOOM').asset_name = ov

# 4. REGISTRATION
classes = (
	DAE_OT_RunChecks,
	DAE_OT_SelectAsset,
	DAE_OT_SelectMaterial,
	DAE_PT_PreFlightPanel,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
