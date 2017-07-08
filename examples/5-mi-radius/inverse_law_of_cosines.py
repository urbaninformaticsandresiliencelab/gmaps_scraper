#!/usr/bin/env python3

import math
import time

RADIUS_OF_EARTH = 6371000

def law_of_cosines(lon1, lat1, lon2, lat2, *extra_args):
    (lat1, lon1, lat2, lon2) = map(math.radians, [lat1, lon1, lat2, lon2])
    return (
        math.acos(
            (math.sin(lat1) * math.sin(lat2))
            + (math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)))
        * RADIUS_OF_EARTH
    )

def inverse_law_of_cosines(lon, lat, radius, tolerance = 1e-10):
    """ Given an origin latitude and longitude, return the bounding box of
    extreme lats/longs and their corresponding longs/lats

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

    extremes = []

    for component in range(4):
        trial_coords = (lon, lat)
        increment = 1
        direction = 1
        previous_direction = 0

        while True:
            current_radius = law_of_cosines(lon, lat, *trial_coords)
            current_precision = current_radius - radius

            if (
                (abs(current_precision) < tolerance)
                and (previous_direction is not 0)
            ):
                extremes.append(trial_coords)
                break
            elif (current_radius > radius):
                if (previous_direction == 1):
                    increment /= 2
                direction = -1
            else:
                if (previous_direction == -1):
                    increment /= 2
                direction = 1
            previous_direction = direction

            if ((component % 2) == 0):
                trial_coords = (
                    trial_coords[0] + (direction * increment),
                    trial_coords[1]
                )
            else:
                trial_coords = (
                    trial_coords[0],
                    trial_coords[1] + (direction * increment)
                )

            time.sleep(0.01)

    return extremes

boston_bbox = (-71.191155, 42.227926, -70.748802, 42.400819999999996)
radius_of_boston = law_of_cosines(*boston_bbox)
print("Radius of Boston: %d" % radius_of_boston)

extremes = inverse_law_of_cosines(
    lon = (boston_bbox[0] + boston_bbox[2])/2,
    lat = (boston_bbox[1] + boston_bbox[3])/2,
    radius = radius_of_boston
)
print(extremes)
