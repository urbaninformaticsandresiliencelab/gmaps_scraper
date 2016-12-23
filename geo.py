#!/usr/bin/env python
# Library for various functions related to latitude/longitude like the haversine
# function

from math import degrees, radians, cos, sin, acos, asin, sqrt
import numpy

radius_of_earth = 6371000

#stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    m = radius_of_earth * c
    return m

def law_of_cosines(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    return acos(sin(lat1) * sin(lat2)
                + cos(lat1) * cos(lat2) * cos(lon2 - lon1)) * radius_of_earth

# Modified from http://pythonfiddle.com/this-is-reverse-haversine/
# Takes an initial latitude or longitude and specified radius and returns the
# domain of possible latitudes or longitudes
# The formula finds the domain of longitudes given a longitude but can be
# generalized to latitudes because of the symmetry of a circle
def inv_haversine_domain(l, radius):
    l = radians(l)
    m = radius / radius_of_earth
    a = (sin(m/2))**2
    return map(degrees, [(2 * asin(-sqrt(a))) + l, (2 * asin(sqrt(a))) + l])

## TODO: work-in-progress below this point #####################################

# Given a lon1, lat1, a component of a point on a circle (l), and a radius, find
# the corresponding coordinate
# lon1 and lat1 are the center point of the circle; l is either the x or y
# component of a point on the circle; the function returns the other two
# possible components
# The formula finds the longitudes corresponding to a given latitude but can be
# generalized to finding latitudes because of the symmetry of a circle
def inv_haversine_component(lon1, lat1, l, radius):
    lat1, l = map(radians, [lat1, l])
    m = radius / radius_of_earth
    a = (sin(m/2))**2
    print(abs(a - sin((l - lat1)/2)**2)) / (cos(lat1) * cos(l))
    s = sqrt((abs(a - sin((l - lat1)/2)**2))/(cos(lat1) * cos(l)))
    lon_temp = map(degrees, [2 * asin(s), 2 * asin(-s)])
    return [lon_temp[0] + lon1, lon_temp[1] + lon1]

'''
def inv_law_of_cosines(lon1, lat1, lat2, radius):
    lon1, lat1, lat2 = map(radians, [lon1, lat1, lat2])
    m = radius / radius_of_earth
    print( acos((cos(m) - sin(lat1) * sin(lat2)) / (cos(lat1) * cos(lat2)) - 1e-15 ))
    lon2 = acos((cos(m) - sin(lat1) * sin(lat2))/(cos(lat1) * cos(lat2)) - 1e-15) + lon1
    return map(degrees, [-lon2, lon2])
'''

# Given a center and a radius, give an array of points on the circle
# The resolution is the number of longitudes; each longitude has a corresponding
# positive latitude and negative latitude, so the total number of points
# returned is resolution * 2 - 2 (two duplicate points are excluded)
def inv_haversine_circle(center_lon, center_lat, radius, resolution = 100):

    points = []

    '''
    points_left = []
    lat_domain = inv_haversine_domain(center_lon, radius)
    for circle_lat in numpy.linspace(lat_domain[0], lat_domain[1], resolution):
        circle_lon1, circle_lon2 = inv_haversine_component(center_lon, center_lat,
                                                           circle_lat, radius)
        points.append([circle_lon1, circle_lat])
        points_left.append([circle_lon2, circle_lat])
    # Merge the points and points_below table such that coordinates are
    # adjacent to each other
    # The first and last items in the list are skipped because they are
    # duplicates
    for i in range(len(points_left) - 1):
        points.append(points_left[len(points_left) - 1 - i])
    '''

    points_below = []
    lon_domain = inv_haversine_domain(center_lon, radius)
    for circle_lon in numpy.linspace(lon_domain[0], lon_domain[1], resolution):
        circle_lat_1, circle_lat_2 = inv_haversine_component(center_lat, center_lon,
                                                             circle_lon, radius)
        points.append([circle_lon, circle_lat_1]) # Latitudes above the center
        points_below.append([circle_lon, circle_lat_2]) # Latitudes below the center

    # Merge the points and points_below table such that coordinates are
    # adjacent to each other
    # The first and last items in the list are skipped because they are
    # duplicates
    for i in range(len(points_below) - 2):
        points.append(points_below[len(points_below) - 2 - i])

    return points
