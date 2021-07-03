# Import of ASCII Grid (.asc) for Blender
# Installs import menu entry in Blender
#
# Georef code based on code of
# "author": "Vladimir Elistratov <prokitektura+support@gmail.com>",
# "wiki_url": "https://github.com/vvoovv/blender-gpx/wiki/Documentation",
#
# Magnus Heitzler hmagnus@ethz.ch
# Hans Rudolf Bär    hbaer@ethz.ch
# 24/10/2015
# 25/11/2016 Models now correctly centered
# 22/10/2019 Ported to blender 2.80
# 19/04/2020 Ported to blender 2.82a, fixed the face/vertex issue.
# 21/04/2020 added georef fixed scale, added missing tiles.
#
# Institute of Cartography and Geoinformation
# ETH Zurich

import pyproj
import numpy
import bmesh
from bpy_extras.io_utils import ImportHelper
import math
import os
import bpy
import sys

bl_info = {
    "name": "Import ASCII (.asc)",
    "author": " M. Heitzler and H. R. Baer",
    "blender": (2, 80, 0),
    "version": (1, 0, 1),
    "location": "File > Import > ASCII (.asc)",
    "description": "Import meshes in ASCII Grid file format",
    "warning": "",
    "wiki_url": "https://github.com/hrbaer/Blender-ASCII-Grid-Import",
    "tracker_url": "https://github.com/hrbaer/Blender-ASCII-Grid-Import/issues",
    "support": "COMMUNITY",
    "category": "Import-Export",
}


_isBlender280 = bpy.app.version[1] >= 80

class CustomProjection:

    def __init__(self, **kwargs):
        # setting default values
        self.lat = 0 # in degrees
        self.lon = 0 # in degrees
        self.utm30N = pyproj.Proj('+init=epsg:25830')   # UTM30N
        self.wgs84 =  pyproj.Proj('+init=epsg:4326')    # WGS84/Geographic

        for attr in kwargs:
            setattr(self, attr, kwargs[attr])

        # generate the x,y point of the "center" of projection
        self.utmx, self.utmy = pyproj.transform(self.wgs84, self.utm30N, self.lon, self.lat)

    def fromGeographic(self, lat, lon):
        # from WGS84 to utm
        point = (lon,lat)
        point_r = pyproj.transform(self.wgs84, self.utm30N, *point)
        point_r = ( point_r[0]-self.utmx, point_r[1]-self.utmy )
        return(point_r)

    def toGeographic(self, x, y):
        # from UTM to WGS84
        # not tested
        point = (x,y)
        point_r = pyproj.transform(self.utm30N, self.wgs84, *point)
        return (point_r[0]+self.lon, point_r[0].self.lat)




class ImportGrid(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.asc"
    bl_label = "Import ASCII Grid"
    bl_options = {'PRESET'}

    filename_ext = ".asc"

    filepath = bpy.props.StringProperty(subtype="FILE_PATH")

    filter_glob = bpy.props.StringProperty(
        default="*.asc",
        options={"HIDDEN"},
    )

    ignoreGeoreferencing = bpy.props.BoolProperty(
        name="Ignore existing georeferencing",
        description="Ignore existing georeferencing and make a new one",
        default=False,
    )


    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):

        FILEHEADERLENGTH = 6


        # Load file
        filename = self.filepath
        f = open(filename, "r")
        content = f.readlines()

        cols = int(content[0].split()[1])
        rows = int(content[1].split()[1])
        xllcorner = float(content[2].split()[1])
        yllcorner = float(content[3].split()[1])
        cellsize = float(content[4].split()[1])
        nodata = float(content[5].split()[1])


        #
        # georef can be from center, or corner, based on
        # the following fields. Can be set at "Center" or
        # "corner". They do reference to the lower left
        # point of the map. Center= center of the cell
        # corner, the lower left point in the grid. so
        # we have to measure what is the origin of the
        # grid
        #
        # XLLCENTER 313670
        # YLLCENTER 4447850
        # xllcorner    314730.619071083551
        # yllcorner    4458361.610961413942

        # first, assume it's corner. (X,Y) lower left (south, west)
        grid_sw = (xllcorner, yllcorner)

        center_or_corner = content[2].split()[0].lower()
        if center_or_corner.find('center') != -1:
            # it's center so adjust it
            grid_sw = (xllcorner-(cellsize/2.0), yllcorner-(cellsize/2.0))


        # calculate size on meters, assume UTM projection N30 (meters)
        # xllcorner, yllcorner are the reference point values to geolocate it.
        width = cols * cellsize
        height = rows * cellsize
        

        # the upper right (north, east)
        grid_ne = ( grid_sw[0] + width, grid_sw[1] + height)

        # Mesh scaling
        data = " ".join(content[FILEHEADERLENGTH:]).strip().split()
        vertices = []
        faces = []
        data = data[:rows*cols]    # get only the real chars

        #
        # reconvert the array, so we have all the required vertex
        # to do that, build a numpy array, reshape to 2d array,
        # copy first the last column, then copy the last row,
        # at last, build again a list.
        #
        # Ncols,Nrows faces have Ncols+1,Nrows+1 vertex
        #

        arr = numpy.array(data)
        arr = numpy.reshape(arr, (rows, cols))
        arr = numpy.insert(arr, cols, values=arr[:, cols-1], axis=1)
        arr = numpy.insert(arr, rows, values=arr[rows-1, :], axis=0)

        new_len = (cols*rows) + rows + cols + 1
        arr = numpy.reshape(arr, new_len)

        # Create vertices
        index = 0
        for r in range(rows, -1, -1):
            for c in range(0, cols+1):
                    vertices.append((c*cellsize, r*cellsize, float(arr[index])))
                    index += 1

        # Construct faces
        index = 0
        for r in range(0, rows):
            for c in range(0, cols):
                v1 = index
                v2 = v1 + (cols+1)
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
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = ob
        ob.select_set(True)

        # geolocate and measure

        grid_center = ( grid_sw[0] + (width/2),  grid_sw[1] + (height/2) )

        dest_utm30N = pyproj.Proj('+init=epsg:25830')    # UTM30N
        target_wgs84 = pyproj.Proj('+init=epsg:4326')    # WGS84/Geographic

        maxLon, minLat = pyproj.transform(dest_utm30N, target_wgs84, *grid_sw)
        minLon, maxLat = pyproj.transform(dest_utm30N, target_wgs84, *grid_ne)
        cenLon, cenLat = pyproj.transform(dest_utm30N, target_wgs84, *grid_center)

        # calculate the projection centering in the origin of blender
        projection = self.getProjection(context, lat = cenLat, lon = cenLon)

        # calculate the position of the origin
        offset_x, offset_y = projection.fromGeographic(minLat, maxLon)
        bpy.ops.transform.translate(value = (offset_x,offset_y,0))

        print("Grid width, height (m): ", width, height)
        print("Origin (SW)", grid_sw, maxLon, minLat)
        print("Corner (NE)", grid_ne, minLon, maxLat)
        print("Center", grid_center, cenLon, cenLat)
        print("Offset ", offset_x, offset_y)

        # Transform mesh
        #bpy.ops.transform.resize(value = (width, height, 1))
        #bpy.ops.transform.translate(value = (-width / 2.0, height / 2.0, 0))

        # Setting data
        me.from_pydata(vertices, [], faces)

        ## delete nodata verts ## experimental work
        bm = bmesh.new()
        bm.from_mesh(me)
        verts = [v for v in bm.verts if v.co[2] == nodata]
        bmesh.ops.delete(bm, geom=verts, context="VERTS")
        bm.to_mesh(me)

        # Update mesh with new data
        me.update()

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "ignoreGeoreferencing")
        if self.bpyproj:
            self.bpyproj.draw(context, layout)

    def invoke(self, context, event):
        # check if <bpyproj> is activated and is available in sys.modules
        self.bpyproj = "bpyproj" in (context.preferences.addons if _isBlender280 else context.user_preferences.addons) and sys.modules.get("bpyproj")
        return super().invoke(context, event)

    def getProjection(self, context, lat, lon):
        # get the coordinates of the center of the Blender system of reference
        scene = context.scene
        if "lat" in scene and "lon" in scene and not self.ignoreGeoreferencing:
            lat = scene["lat"]
            lon = scene["lon"]
        else:
            scene["lat"] = lat
            scene["lon"] = lon

        projection = None
        if self.bpyproj:
            projection = self.bpyproj.getProjection(lat, lon)
        if not projection:
            # fall back to the CustomProjection
            projection = CustomProjection(lat=lat, lon=lon)
        return projection

def menu_func(self, context):
    self.layout.operator(ImportGrid.bl_idname, text="ASCII Grid (.asc)")


def register():
    bpy.utils.register_class(ImportGrid)
    if _isBlender280:
        bpy.types.TOPBAR_MT_file_import.append(menu_func)
    else:
        bpy.types.INFO_MT_file_import.append(menu_func)


def unregister():
    bpy.utils.unregister_class(ImportGrid)
    if _isBlender280:
        bpy.types.TOPBAR_MT_file_import.remove(menu_func)
    else:
        bpy.types.INFO_MT_file_import.remove(menu_func)


if __name__ == "__main__":
    register()
