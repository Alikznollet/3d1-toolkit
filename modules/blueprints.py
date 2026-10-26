import bpy
import math
import os

class DAE_OT_ImportBlueprints(bpy.types.Operator):
	bl_idname: str = "dae.import_blueprints"
	bl_label: str = "Generate Blueprint Setup"
	bl_description: str = "Upload images to automatically generate aligned blueprint planes"
	bl_options: set[str] = {'REGISTER', 'UNDO'}

	# These properties create the file browser inputs in the popup
	filepath_front: bpy.props.StringProperty(name="Front View", subtype='FILE_PATH')
	filepath_back: bpy.props.StringProperty(name="Back View", subtype="FILE_PATH")
	filepath_right: bpy.props.StringProperty(name="Right/Side View", subtype='FILE_PATH')
	filepath_left: bpy.props.StringProperty(name="Left/Side View", subtype="FILE_PATH")
	filepath_top: bpy.props.StringProperty(name="Top View", subtype='FILE_PATH')
	filepath_bottom: bpy.props.StringProperty(name="Bottom View", subtype='FILE_PATH')

	def invoke(self, context, event):
		# Spawns a popup window containing our properties
		return context.window_manager.invoke_props_dialog(self, width=400)

	def draw(self, context):
		layout = self.layout
		layout.label(text="Select Blueprint Images:", icon='IMAGE_DATA')
		layout.separator()
		layout.prop(self, "filepath_front")
		layout.prop(self, "filepath_back")
		layout.prop(self, "filepath_right")
		layout.prop(self, "filepath_left")
		layout.prop(self, "filepath_top")
		layout.prop(self, "filepath_bottom")

	def execute(self, context):
		configs = [
			# Front faces -Y (pushed back to +Y)
			(self.filepath_front, "BP_Front", (math.radians(90), 0, 0), (0, 1.0, 0)),
			
			# Back faces +Y (pushed forward to -Y)
			(self.filepath_back, "BP_Back", (math.radians(90), 0, math.radians(180)), (0, -1.0, 0)),
			
			# Right faces +X (pushed left to -X)
			(self.filepath_right, "BP_Right", (math.radians(90), 0, math.radians(90)), (-1.0, 0, 0)),
			
			# Left faces -X (pushed right to +X)
			(self.filepath_left, "BP_Left", (math.radians(90), 0, math.radians(-90)), (1.0, 0, 0)),
			
			# Top faces +Z (pushed down to -Z)
			(self.filepath_top, "BP_Top", (0, 0, 0), (0, 0, -1.0)),
			
			# Bottom faces -Z (pushed up to +Z)
			(self.filepath_bottom, "BP_Bottom", (math.radians(180), 0, 0), (0, 0, 1.0))
		]

		# Create a new collection for the blueprints or get the existing one.
		if "BP" not in bpy.data.collections:
			bp_collection = bpy.data.collections.new("BP")
			bpy.context.scene.collection.children.link(bp_collection)
		else:
			bp_collection = bpy.data.collections["BP"]

		for filepath, name, rotation, offset in configs:
			if not filepath:
				continue # Skip if the user did not add a file.
				
			# Resolve relative paths
			filepath = bpy.path.abspath(filepath)
			
			if not os.path.exists(filepath):
				self.report({'WARNING'}, f"File not found: {filepath}")
				continue

			# Load the image and get it's width and height.
			img = bpy.data.images.load(filepath)
			width, height = img.size
			if width == 0 or height == 0:
				continue

			# Calculate the aspect radio of the image.
			aspect_x = width / max(width, height)
			aspect_y = height / max(width, height)

			# Spawn a Plane with correct rotation
			bpy.ops.mesh.primitive_plane_add(size=2.0, rotation=rotation, location=offset)
			plane = context.active_object
			plane.name = name

			# Link the plane to the correct collection
			if plane.name not in bp_collection.objects:
				bp_collection.objects.link(plane)

			# Unlink it from whatever it spawned in.
			for coll in plane.users_collection:
				if coll != bp_collection:
					coll.objects.unlink(plane)
			
			# Scale to aspect ratio and apply
			plane.scale = (aspect_x, aspect_y, 1.0)
			bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

			# Create and assign Material
			mat = bpy.data.materials.new(name=f"M_{name}")
			mat.use_nodes = True
			mat.use_backface_culling = True
			bsdf = mat.node_tree.nodes.get("Principled BSDF")

			# Add the texture.
			tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
			tex_node.image = img

			# Link up the shader nodes.
			mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
			plane.data.materials.append(mat)

		self.report({'INFO'}, "Blueprints generated successfully.")
		return {'FINISHED'}

classes = (
    DAE_OT_ImportBlueprints,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
