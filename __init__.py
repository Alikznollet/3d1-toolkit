import bpy
import bmesh

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
					box.label(text=n)
					
			# Display Material Errors
			if report_cache["materials"]:
				box = layout.box()
				box.label(text="Missing 'M_' Prefix:", icon='ERROR')
				for m in report_cache["materials"]: 
					box.label(text=m)
					
			# Display N-Gon Errors
			if report_cache["ngons"]:
				box = layout.box()
				box.label(text="Contains N-Gons:", icon='ERROR')
				for g in report_cache["ngons"]: 
					box.label(text=g)

			# Display Non-Manifolds Errors
			if report_cache["non-manifolds"]:
				box = layout.box()
				box.label(text="Contains Non-Manifolds:", icon='ERROR')
				for g in report_cache["non-manifolds"]: 
						box.label(text=g)

			# Display Overlapping Geometry Errors
			if report_cache["overlapping"]:
				box = layout.box()
				box.label(text="Overlapping Verts/Faces:", icon='ERROR')
				for ov in report_cache["overlapping"]: 
					box.label(text=ov)

# 4. REGISTRATION
classes = (
    DAE_OT_RunChecks,
    DAE_PT_PreFlightPanel,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
