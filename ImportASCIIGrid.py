# Import of ASCII Grid (.asc) for Blender
# Installs import menu entry in Blender

# Magnus Heitzler hmagnus@ethz.ch
# Hans Rudolf Bär  hbaer@ethz.ch
# 14/08/2015
# Institute of Cartography and Geoinformation
# ETH Zurich

bl_info = {
  "name": "Import ASCII Grid",
  "author": " M. Heitzler and H. R. Baer",
  "blender": (2,6,2),
  "version": (0,0,1),
  "location": "File>Import-Export",
  "description": "Import meshes in ASCII Grid file format",
  "category": "Import-Export"
}

import bpy
import os
import math

class ImportAsciiGrid(bpy.types.Operator):
  bl_idname = "import_grid_format.asc"
  bl_label = "Import ASCII Grid"
  bl_options = {'PRESET'}

  filename_ext = ".asc";

  filepath = bpy.props.StringProperty(subtype="FILE_PATH")

  @classmethod
  def poll(cls, context):
    return True

  def execute(self, context):

    FILEHEADERLENGTH = 6
    SCALE = 10

    # Load file
    filename = self.filepath
    f = open(filename, "r")
    content = f.readlines()

    cols = int(content[0].split()[1])
    rows = int(content[1].split()[1])
    cellsize = float(content[4].split()[1])

    # Mesh scaling
    size = math.sqrt(float((cols - 1) * (rows - 1)))
    scale_cols = SCALE * (size / (rows - 1))
    scale_rows = SCALE * (size / (cols - 1))
    scale_vals = scale_cols / (cellsize * float(cols - 1))

    data = " ".join(content[FILEHEADERLENGTH:]).split()
    vertices = []
    faces = []

    # Create vertices
    index = 0;
    for r in range(0, rows):
      for c in range(0, cols):
        vertices.append((r, c, float(data[index])))
        index += 1

    # Construct faces
    index = 0
    for r in range(0, rows - 1):
      for c in range(0, cols - 1):
        v1 = index
        v2 = v1 + cols
        v3 = v2 + 1
        v4 = v1 + 1
        faces.append((v1, v2, v3, v4))
        index += 1
      index += 1

    # Create mesh
    name = os.path.splitext(os.path.basename(filename))[0]
    me = bpy.data.meshes.new(name)
    ob = bpy.data.objects.new(name, me)
    ob.location = (0, 0, 0)
    ob.show_name = True

    # Link object to scene and make active
    scn = bpy.context.scene
    scn.objects.link(ob)
    scn.objects.active = ob
    ob.select = True

    # Transform mesh
    bpy.ops.transform.resize(value = (scale_rows / (rows - 1), scale_cols / (cols - 1), scale_vals))
    bpy.ops.transform.translate(value = (-0.5 * scale_rows, -0.5 * scale_cols, 0))

    # Setting data
    me.from_pydata(vertices, [], faces)

    # Update mesh with new data
    me.update()

    return {'FINISHED'}

  def invoke(self, context, event):
    context.window_manager.fileselect_add(self)
    return {'RUNNING_MODAL'}

def menu_func(self, context):
  self.layout.operator(ImportAsciiGrid.bl_idname, text="ASCII Grid (.asc)")

def register():
  bpy.utils.register_module(__name__)
  bpy.types.INFO_MT_file_import.append(menu_func)

def unregister():
  bpy.utils.uregister_class(__name__)
  bpy.types.INFO_MT_file_import.remove(menu_func)


if __name__ == "__main__":
  register()
