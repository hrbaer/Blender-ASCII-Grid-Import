# Import of ASCII Grid (.asc) for Blender
# Installs import menu entry in Blender

# Magnus Heitzler hmagnus@ethz.ch
# Hans Rudolf Bär  hansruedi.baer@bluewin.ch
# 24/10/2015
# 25/11/2016 Models now correctly centered
# 22/10/2019 Ported to Blender 2.80
# 19/06/2022 Ported to Blender 3.2
# Institute of Cartography and Geoinformation
# ETH Zurich

bl_info = {
  "name": "Import ASCII (.asc)",
  "author": " M. Heitzler and H. R. Baer",
  "blender": (3, 2, 0),
  "version": (1, 0, 2),
  "location": "File > Import > ASCII (.asc)",
  "description": "Import meshes in ASCII Grid file format",
  "warning": "",
  "wiki_url": "https://github.com/hrbaer/Blender-ASCII-Grid-Import",
  "tracker_url": "https://github.com/hrbaer/Blender-ASCII-Grid-Import/issues",
  "support": "COMMUNITY",
  "category": "Import-Export",
}

import bpy
import os
import math
from bpy_extras.io_utils import ImportHelper

class ImportGrid(bpy.types.Operator, ImportHelper):
  bl_idname = "import_scene.asc"
  bl_label = "Import ASCII Grid"
  bl_options = {'PRESET'}

  filename_ext = ".asc";

  filepath = bpy.props.StringProperty(subtype="FILE_PATH")

  filter_glob = bpy.props.StringProperty(
      default="*.asc",
      options={"HIDDEN"},
  )

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
    scale_xy = SCALE / float(cols - 1)
    scale_z = SCALE / (cellsize * float(cols - 1))

    data = " ".join(content[FILEHEADERLENGTH:]).split()
    vertices = []
    faces = []

    # Create vertices
    index = 0;
    for r in range(rows - 1, -1, -1):
      for c in range(0, cols):
        vertices.append((c, r, float(data[index])))
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
    col = bpy.context.collection
    col.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)

    # Transform mesh
    bpy.ops.transform.resize(value = (scale_xy, scale_xy, scale_z))
    bpy.ops.transform.translate(value = (-scale_xy * (cols - 1) / 2.0, -scale_xy * (rows - 1) / 2.0, 0))

    # Setting data
    me.from_pydata(vertices, [], faces)

    # Update mesh with new data
    me.update()

    return {'FINISHED'}

  def draw(self, context):
      layout = self.layout

  def invoke(self, context, event):
    #context.window_manager.fileselect_add(self)
    #return {'RUNNING_MODAL'}
    return super().invoke(context, event)


def menu_func(self, context):
  self.layout.operator(ImportGrid.bl_idname, text="ASCII Grid (.asc)")


def register():
    bpy.utils.register_class(ImportGrid)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ImportGrid)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)
  
if __name__ == "__main__":
  register()
