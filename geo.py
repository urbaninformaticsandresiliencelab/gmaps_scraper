#!/usr/bin/env python
# Library for various functions related to latitude/longitude like the haversine
# function

from math import degrees, radians, cos, sin, acos, asin, sqrt
import numpy

RADIUS_OF_EARTH = 6371000

def point_in_polygon(point, polygon):
    """ Determine whether a point lies within a polygon

    Determines whether a point lies within a polygon by casting a horizontal ray
    to the right and counting the number of intersections with line segments. If
    there are an odd number of intersections, the point lies inside; otherwise,
    the point lies outside.

    Args:
        point: A (longitude, latitude) coordinate pair to be tested.
        polygon: An array of coordinate pairs representing the polygon. The last
            line segment is created between the first item in the array and the
            last item in the array.

    Returns:
        True if the point lies within the polygon; False otherwise.
    """

    intersections = 0
    num_coordinate_pairs = len(polygon)

    for i in range(num_coordinate_pairs):
        lng = [polygon[i][0]]
        lat = [polygon[i][1]]

        if (i == (num_coordinate_pairs - 1)):
            lng.append(polygon[0][0])
            lat.append(polygon[0][1])
        else:
            lng.append(polygon[i + 1][0])
            lat.append(polygon[i + 1][1])

        # The smaller point should be the bottom-left point
        lng = sorted(lng)
        lat = sorted(lat)

        # The ray intersects with the line segment if:
        #     lat_1 <= point_lat <= lat_2
        #     point_lng <= the average of lng_1 and lng_2
        if ((point[1] >= lat[0])
            and (point[1] <= lat[1])
            and (point[0] <= (lng[0]+lng[1])/2)):
            intersections += 1

    if (intersections % 2):
        return True
    else:
        return False

def haversine(lon1, lat1, lon2, lat2):
    """ Calculate the distance between two points on a sphere using the
    haversine forumula

    From:
    stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points

    Args:
        lon1, lat1: Floating point components of the first coordinate pair.
        lon2, lat2: Floating point components of the second coordinate pair.

    Returns:
        A floating point representing the distance between the two points, in
            meters.
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    m = RADIUS_OF_EARTH * c
    return m

def law_of_cosines(lon1, lat1, lon2, lat2):
    """ Calculate the distance between two points on a sphere using the law of
    cosines

    Args:
        lon1, lat1: Floating point components of the first coordinate pair.
        lon2, lat2: Floating point components of the second coordinate pair.

    Returns:
        A floating point representing the distance between the two points, in
            meters.
    """
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    return acos(sin(lat1) * sin(lat2)
                + cos(lat1) * cos(lat2) * cos(lon2 - lon1)) * RADIUS_OF_EARTH
