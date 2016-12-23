#!/usr/bin/env python
# Small library for generating URLs of visualizations

# This points array acts as a buffer for the current visualization.
points = []

# Only generates paths for now - generate a Google Static Maps API URL from the
# global points table
def generate_url(color = "0xff0000"):
    url = "https://maps.googleapis.com/maps/api/staticmap?size=400x400&path=color:%s|weight:5" % color
    x = []
    y = []

    for point in points:
        url += "|%f,%f" % (point[1], point[0])
        x.append(point[1])
        y.append(point[0])

    return url

# Add points to the global points array. Points can be supplied one at a time or
# in an array
def add_points(new_points):
    global points
    if (type(new_points[0]) is list) or (type(new_points[0]) is tuple):
        points += new_points
    else:
        points.append(new_points)

# Clear the global points array
def reset_points():
    global points
    points = []
