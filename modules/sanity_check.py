import bpy
import bmesh
from enum import Enum

class Check(Enum):
	OBJECT_NAMING = ("SM_ Prefix", "dae.select_object", "OUTLINER_OB_MESH")
	MATERIAL_NAMING = ("M_ Prefix", "dae.select_material", "MATERIAL")
	NGONS = ("N-Gons", "dae.select_object", "MESH_DATA")
	NON_MANIFOLDS = ("Non-Manifolds", "dae.select_object", "MOD_WIREFRAME")
	OVERLAPPING_GEOMETRY = ("Overlapping Geometry", "dae.select_object", "OVERLAY")
	UNAPPLIED_MODIFIERS = ("Unapplied Modifiers", "dae.select_object", "MODIFIER_DATA")
	UNUSED_MATERIALS = ("Unused Materials", "", "MATERIAL")
	UNUSED_TEXTURES = ("Unused Textures", "", "IMAGE_DATA")
	PSD_TEXTURES = ("PSD Textures", "", "FILE_IMAGE")

class Category(Enum):
	NAMING = "Naming"
	MESH = "Mesh"
	DATA = "Data"

# List of keys accompanied by their labels and icons.
CATEGORIES: dict[Category, list[Check]] = {
	Category.NAMING: [Check.OBJECT_NAMING, Check.MATERIAL_NAMING],
	Category.MESH: [Check.NGONS, Check.NON_MANIFOLDS, Check.OVERLAPPING_GEOMETRY, Check.UNAPPLIED_MODIFIERS],
	Category.DATA: [Check.UNUSED_MATERIALS, Check.UNUSED_TEXTURES, Check.PSD_TEXTURES]
}

# Whether the checks have been ran once before.
ran_once: bool = False
report_cache: dict[Check, list[str]] = {} # Dynamic dict of values

class DAE_OT_SanityCheckPopup(bpy.types.Operator):
	bl_idname = "dae.run_sanity_check"
	bl_label = "DAE 3D1 Sanity Checker"

	def invoke(self, context, event): 
		# Force into object mode so edits are applied
		if context.active_object and context.active_object.mode != "OBJECT":
			bpy.ops.object.mode_set(mode="OBJECT")

		# Clear and initialize the cache
		for cat in CATEGORIES:
			for check in CATEGORIES[cat]:
				if check not in report_cache:
					report_cache[check] = []
				report_cache[check].clear()

		# Scan Objects
		for obj in bpy.context.scene.objects:
			if obj.type == "MESH":
				# Check the Prefix
				if not obj.name.startswith("SM_"):
					report_cache[Check.OBJECT_NAMING].append(obj.name)

				# Check if there are any modifiers still not applied.
				if len(obj.modifiers) > 0:
					report_cache[Check.UNAPPLIED_MODIFIERS].append(obj.name)

				# We'll copy the mesh.
				bm = bmesh.new()
				bm.from_mesh(obj.data)

				# Check for n-gons too.
				if any(len(p.vertices) > 4 for p in obj.data.polygons):
					report_cache[Check.NGONS].append(obj.name)

				# Check for non-manifolds.
				for edge in bm.edges:
					# Flag edges that have no faces or more than 2.
					if not edge.is_manifold and not edge.is_boundary:
						report_cache[Check.NON_MANIFOLDS].append(obj.name)
						break

				# Check for overlapping edges.
				original_vert_count = len(bm.verts)

				# Run a merge by distance on the copied mesh.
				bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

				# If the count went down there's overlapping vertices.
				if len(bm.verts) < original_vert_count:
					report_cache[Check.OVERLAPPING_GEOMETRY].append(obj.name)

				# Delete the bmesh
				bm.free()

		# Scan Materials
		used_textures = set()
		for mat in bpy.data.materials:
			# Check for material naming.
			if not mat.name.startswith("M_") and not mat.name.startswith("Dots"):
				report_cache[Check.MATERIAL_NAMING].append(mat.name)

			# Check if the material even has users.
			if mat.users == 0:
				report_cache[Check.UNUSED_MATERIALS].append(mat.name)

			# We check for textures so we can determine unused textures later.
			if mat.use_nodes:
				for node in mat.node_tree.nodes:
					if node.type == "TEX_IMAGE" and node.image:
						used_textures.add(node.image)

		# Scan the textures/images
		for texture in bpy.data.images:
			# Ignore blender internals	
			if texture.type not in ("IMAGE", "UV_TEST") or texture.source not in ("FILE", "GENERATED"):
				continue

			# Check for unused ones.
			if texture not in used_textures:
				report_cache[Check.UNUSED_TEXTURES].append(texture.name)

			# Check for psd format
			filepath = texture.filepath.lower()
			if filepath.endswith(".psd") or texture.name.lower().endswith(".psd"):
				report_cache[Check.PSD_TEXTURES].append(texture.name)

		return context.window_manager.invoke_popup(self, width=280)

	def execute(self, context):
		return {"FINISHED"}

	def draw(self, context):
		layout = self.layout
		layout.label(text="Is your asset ready?")

		for cat in CATEGORIES:
			checks: list[Check] = CATEGORIES[cat]

			# Add the category label
			layout.separator()
			layout.label(text=f"{cat.value}", icon="INFO")

			# Loop over all of the checks in a category
			for check in checks:
				box = layout.box()

				# Check if that check has issues. If not tell the user the check passed.
				if report_cache[check]:
					box.label(text=f"{check.value[0]}:", icon="ERROR")
					col = box.column(align=True)
					for report in report_cache[check]:
						if check.value[1] != "":
							op = col.operator(check.value[1], text=report, icon=check.value[2])
							op.target = report
						else:
							col.label(text=report, icon=check.value[2])
				else:
					box.label(text=f"{check.value[0]}: Passed", icon="CHECKMARK")

class DAE_OT_SelectObject(bpy.types.Operator):
	bl_idname = "dae.select_object"
	bl_label = "Select Asset"

	target: bpy.props.StringProperty()

	def execute(self, context):
		if context.active_object and context.active_object.mode != "OBJECT":
			bpy.ops.object.mode_set(mode="OBJECT")

		# Deselect all previous objects
		bpy.ops.object.select_all(action="DESELECT")

		# Select the object if one exists.
		obj = bpy.data.objects.get(self.target)
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

	target: bpy.props.StringProperty()

	def execute(self, context):
		target_mat = bpy.data.materials.get(self.target)
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

			self.report({"INFO"}, f"Selected {len(found_objects)} objects using material '{self.target}'.")
		else:
			self.report({"WARNING"}, f"Material '{self.target}' had 0 users.")

		return {"FINISHED"}

classes = (
	DAE_OT_SanityCheckPopup,
    DAE_OT_SelectObject,
    DAE_OT_SelectMaterial,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
				
