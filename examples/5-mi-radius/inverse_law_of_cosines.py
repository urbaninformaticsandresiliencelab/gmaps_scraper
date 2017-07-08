#!/usr/bin/env python3

import json
import math
import time

RADIUS_OF_EARTH = 6371000

def law_of_cosines(lon1, lat1, lon2, lat2):
    """ Calculate the great circle distance between two geographical
    coordinates

    Args:
        lon1, lat1: The origin coordinate components
        lon2, lat2: The destination coordinate components

    Returns:
        The distance between (lon1, lat1) and (lon2, lat2), in meters.
    """

    (lon1, lat1, lon2, lat2) = map(math.radians, [lon1, lat1, lon2, lat2])

    return (
        math.acos(
            (math.sin(lat1) * math.sin(lat2))
            + (math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)))
        * RADIUS_OF_EARTH
    )

def inverse_law_of_cosines(lon, lat, radius, tolerance = 1e-6):
    """ Given an origin latitude and longitude, return the bounding box of
    extreme lats/longs and their corresponding longs/lats

    This is not a *true* implementation of an inverse law of cosines, as it
    only focuses on points with extreme longitudes or latitudes (theta = 0,
    pi/2, pi, and 3pi/2).

    The algorithm works by first doing a binary search for the point with max
    longitude and a search for the point with max latitude. The algorithm then
    calculates the difference in degree between these points and the origin
    point to find the point with min longitude and the point with max
    longitude - the max and min longitudes should be equally far apart from the
    origin, as should the max and min latitudes.

    Args:
        lat: The latitude of the origin point
        lon: The longitude of the origin point
        radius: The radius of the circle to calculate, in meters
        tolerance: The smallest number of the geospatial degree to which an
            error can be tolerated

    Returns:
        An array of (lon, lat) pairs representing the leftmost coordinate, the
        bottommost coordinate, the rightmost coordinate, and the topmost
        coordinate of the possible range of coordinates
    """

    extremes = {}

    for component in ["max_longitude", "max_latitude"]:
        trial_coords = (lon, lat)
        increment = 1
        direction = 0
        previous_direction = 0

        while True:
            current_radius = law_of_cosines(lon, lat, *trial_coords)
            current_precision = current_radius - radius

            # within tolerance
            if (
                (abs(current_precision) < tolerance)
                and (previous_direction is not 0)
            ):
                extremes[component] = trial_coords
                break

            # oscillating behaviour: decrease the increment and change the
            # direction
            elif (current_radius > radius):
                if (previous_direction == 1):
                    increment /= 2
                direction = -1
            else:
                if (previous_direction == -1):
                    increment /= 2
                direction = 1
            previous_direction = direction

            # adjust the trial coordinates to be closer to the goal
            if (component == "max_longitude"):
                trial_coords = (
                    trial_coords[0] + (direction * increment),
                    trial_coords[1]
                )
            else:
                trial_coords = (
                    trial_coords[0],
                    trial_coords[1] + (direction * increment)
                )

    extremes["min_longitude"] = (
        lon - (extremes["max_longitude"][0] - lon), lat
    )
    extremes["min_latitude"] = (
        lon, lat - (extremes["max_latitude"][1] - lat)
    )

    return extremes

if (__name__ == "__main__"):
    boston_bbox = (-71.191155, 42.227926, -70.748802, 42.400819999999996)
    radius_of_boston = law_of_cosines(*boston_bbox)/2
    print("Radius of Boston: %d" % radius_of_boston)

    extremes = inverse_law_of_cosines(
        lon = (boston_bbox[0] + boston_bbox[2])/2,
        lat = (boston_bbox[1] + boston_bbox[3])/2,
        radius = radius_of_boston
    )
    print("Extremes: %s" % extremes)
    print("GeoJSON: %s" % json.dumps({
        "type": "Polygon",
        "coordinates": [[
            extremes[key] for key in ["min_longitude", "min_latitude",
                                      "max_longitude", "max_latitude"]
        ]]
    }))
