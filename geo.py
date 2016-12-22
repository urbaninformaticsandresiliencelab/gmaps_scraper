#!/usr/bin/env python
# Library for various functions related to latitude/longitude like the haversine
# function

from math import degrees, radians, cos, sin, asin, sqrt
import numpy

#stackoverflow.com/questions/4913349/haversine-formula-in-python-bearing-and-distance-between-two-gps-points
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    m = 6367000 * c
    return m

# Modified from http://pythonfiddle.com/this-is-reverse-haversine/
# Takes an initial latitude or longitude and specified radius and returns the
# domain of possible latitudes or longitudes
def inv_haversine_domain(l, radius):
    l = radians(l)
    m = radius / 6367000
    a = (sin(m/2))**2
    return map(degrees, [(2 * asin(-sqrt(a))) + l, (2 * asin(sqrt(a))) + l])

# Given a lon1, lat1, a component of a point on a circle (l), and a radius, find
# the corresponding coordinate
# lon1 and lat1 are the center point of the circle; l is either the x or y
# component of a point on the circle; the function returns the other component
def inv_haversine_component(lon1, lat1, l, radius):
    lat1, l = map(radians, [lat1, l])
    m = radius / 6367000
    a = (sin(m/2))**2
    s = sqrt((abs(a - sin((l - lat1)/2)**2))/(cos(lat1) * cos(l)))
    lon_temp = map(degrees, [2 * asin(s), 2 * asin(-s)])
    return [lon_temp[0] + lon1, lon_temp[1] + lon1]

# Given a center and a radius, give an array of points on the circle
# The resolution is the number of longitudes; each longitude has a corresponding
# positive latitude and negative latitude, so the total number of points
# returned is resolution * 2
def inv_haversine_circle(center_lat, center_lon, radius, resolution = 20):
    lon_domain = inv_haversine_domain(center_lat, radius)
    points = []
    for circle_lon in numpy.linspace(lon_domain[0], lon_domain[1], resolution):
        circle_lat_1, circle_lat_2 = inv_haversine_component(center_lon, center_lat,
                                                             circle_lon, radius)
        points.append([circle_lon, circle_lat_1]) # Latitudes above the center
        points.append([circle_lon, circle_lat_2]) # Latitudes below the center
    return points
