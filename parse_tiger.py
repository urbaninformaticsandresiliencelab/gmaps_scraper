#!/usr/bin/env python

from math import radians, cos, sin, asin, sqrt
import glob, shapefile, re, sys

################################################################################
# Calculate distance between a pair of geographical coordinates, in meters
def haversine(lon1, lat1, lon2, lat2):
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    m = 6367000 * c

    return m

################################################################################
# Given an array of (x, y) coordinates, return the most extreme values
def extract_extents(points):

    # Initial values are set such that any latitude or longitude should be
    # recognized as "more extreme" than the initial value and, thus, should
    # replace the initial value
    min_latitude = 90
    max_latitude = -90
    min_longitude = 180
    max_longitude = -180

    for point in points:

        if (point[1] < min_latitude):
            min_latitude = point[1]
        elif (point[1] > max_latitude):
            max_latitude = point[1]

        if (point[0] < min_longitude):
            min_longitude = point[0]
        elif (point[0] > max_longitude):
            max_longitude = point[0]

    return {
        "min_latitude": min_latitude,
        "max_latitude": max_latitude,
        "min_longitude": min_longitude,
        "max_longitude": max_longitude,
    }

################################################################################
# Parse the given shp_file for info of the shape with the given name, or, if
# none is specified, the info of the shapefile as a whole

# Returns a dictionary of various information about the target shape:
# "name" = target's name
# "center" = the center of the shape

def get_extents(shp_file, target = "full"):

    points = []
    info = {}

    for shape_record in shapefile.Reader(shp_file).shapeRecords():
        # If no target is specified, the points array will consist of the
        # points of all shapes in the given shapefile
        if (target == "full"):
            points += shape_record.shape.points
        # If a target is specified, the points array will consist of only that
        # target's points
        elif (shape_record.record[4] == target):
            points = shape_record.shape.points

    print("%d Points for target \"%s\"" % (len(points), target))

    if (len(points) == 0):
        print("Error: no shape \"%s\" found in %s" % (target, shp_file))
        return False
    else:
        info = extract_extents(points)

        if (target == "full"):
            info["name"] = target
        else:
            info["name"] = target
        return info

'''
# demo
shp_file = glob.glob("tiger-2016/New York/*.shp")[0]
print("Using file %s" % shp_file)
print
print(get_extents(shp_file))
print(get_extents(shp_file, "Albany"))
print(get_extents(shp_file, "Syracuse"))
print(get_extents(shp_file, "New York"))
'''
