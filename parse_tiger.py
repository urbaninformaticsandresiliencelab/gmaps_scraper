#!/usr/bin/env python
# Library for parsing U.S. Census shapefiles

from math import radians, cos, sin, asin, sqrt
import glob, shapefile, re, sys

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


# Get all points belonging to the given shapes
def dump_points(shp_file, name = "all"):
    points = []
    for shape_record in shapefile.Reader(shp_file).shapeRecords():
        if (name == "all") or (shape_record.record[4] == name):
            points += shape_record.shape.points
    return points

# Parse the given shp_file for info of the shape with the given name, or, if
# none is specified, the info of the shapefile as a whole
# Returns a dictionary of various information about the target shape:
# "name" = target's name
# "center" = the center of the shape
def get_extents(shp_file, target = "full"):

    points = []
    info = {}

    # If no target is specified, the points array will consist of the
    # points of all shapes in the given shapefile
    if (target == "full"):
        points = dump_points(shp_file)
    # If a target is specified, the points array will consist of only that
    # target's points
    else:
        points = dump_points(shp_file, target)

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
