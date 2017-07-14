#!/usr/bin/env python3

import csv
import json
import math
import time

API_KEY = "API KEY HERE"

RADIUS_OF_EARTH = 6371000

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
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    m = RADIUS_OF_EARTH * c
    return m

def inverse_haversine(lon, lat, radius, tolerance = 1e-6):
    """ Given an origin latitude and longitude, return the bounding box of
    extreme lats/longs and their corresponding longs/lats

    This is not a *true* implementation of an inverse haversine, as it only
    focuses on points with extreme longitudes or latitudes (theta = 0, pi/2,
    pi, and 3pi/2).

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
        A dictionary containing the extreme longitudes and latitudes
    """

    extremes = {}

    for component in ["max_longitude", "max_latitude"]:
        trial_coords = (lon, lat)
        increment = 1
        direction = 0
        previous_direction = 0

        while True:
            current_radius = haversine(lon, lat, *trial_coords)
            current_precision = current_radius - radius

            # within tolerance
            if (
                (abs(current_precision) < tolerance)
                and (previous_direction is not 0)
            ):
                if (component == "max_longitude"):
                    extremes[component] = trial_coords[0]
                else:
                    extremes[component] = trial_coords[1]
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

    extremes["min_longitude"] = lon - (extremes["max_longitude"] - lon)
    extremes["min_latitude"] = lat - (extremes["max_latitude"] - lat)

    return extremes

def split_bbox(bbox, splits, direction):
    """ Split a gmaps_scraper kwargs bbox kwargs into n parts in a single
    direction

    Args:
        bbox: A gmaps_scraper bbox kwargs dictionary
        splits: The number of splits to make
        direction: Either "vertical" or "horizontal"

    Returns:
        An array of smaller bbox kwargs dictionaries
    """

    results = []

    if (direction == "vertical"):
        lat_segment = ((bbox["max_latitude"] - bbox["min_latitude"]) / splits)
        for i in range(splits):
            results.append({
                "min_longitude": bbox["min_longitude"],
                "min_latitude": bbox["min_latitude"] + (lat_segment * i),
                "max_longitude": bbox["max_longitude"],
                "max_latitude": bbox["min_latitude"] + (lat_segment * (i + 1))
            })

    elif (direction == "horizontal"):
        lon_segment = ((bbox["max_longitude"] - bbox["min_longitude"]) / splits)
        for i in range(splits):
            results.append({
                "min_longitude": bbox["min_longitude"] + (lon_segment * i),
                "min_latitude": bbox["min_latitude"],
                "max_longitude": bbox["min_longitude"] + (lon_segment * (i + 1)),
                "max_latitude": bbox["max_latitude"]
            })

    return results

def bbox_to_geojson(bbox):
    """ Convert gmaps_scraper bbox kwargs into a GeoJSON string

    Args:
        bbox: A gmaps_scraper bbox kwargs dictionary

    Returns:
        A GeoJSON string
    """

    return json.dumps({
            "type": "Polygon",
            "coordinates": [[
                [bbox["max_longitude"], bbox["max_latitude"]],
                [bbox["max_longitude"], bbox["min_latitude"]],
                [bbox["min_longitude"], bbox["min_latitude"]],
                [bbox["min_longitude"], bbox["max_latitude"]],
            ]]
    })

if (__name__ == "__main__"):
    # about 5 miles
    radius_meters = 8046.72

    with open("top50cities.csv", "r") as f:
        for row in csv.DictReader(f):
            city = row.pop("city").lower().replace(" ", "_").replace("/", "_")
            for key in row:
                row[key] = float(row[key])

            northeast = inverse_haversine(
                row["max_longitude"], row["max_latitude"],
                radius_meters
            )
            southwest = inverse_haversine(
                row["min_longitude"], row["min_latitude"],
                radius_meters
            )

            perimeter_bboxes = [
                { # North
                    "min_longitude": southwest["min_longitude"],
                    "min_latitude": row["max_latitude"],
                    "max_longitude": row["max_longitude"],
                    "max_latitude": northeast["max_latitude"]
                },
                { # East
                    "min_longitude": row["max_longitude"],
                    "min_latitude": row["min_latitude"],
                    "max_longitude": northeast["max_longitude"],
                    "max_latitude": northeast["max_latitude"]
                },
                { # South
                    "min_longitude": row["min_longitude"],
                    "min_latitude": southwest["min_latitude"],
                    "max_longitude": northeast["max_longitude"],
                    "max_latitude": row["min_latitude"]
                },
                { # West
                    "min_longitude": southwest["min_longitude"],
                    "min_latitude": southwest["min_latitude"],
                    "max_longitude": row["min_longitude"],
                    "max_latitude": row["max_latitude"]
                }
            ]

            # The perimeter bounding boxes are too elongated, so we need to
            # split them a little
            scraping_bboxes = []
            scraping_bboxes += split_bbox(perimeter_bboxes[0], 3, "horizontal")
            scraping_bboxes += split_bbox(perimeter_bboxes[1], 3, "vertical")
            scraping_bboxes += split_bbox(perimeter_bboxes[2], 3, "horizontal")
            scraping_bboxes += split_bbox(perimeter_bboxes[3], 3, "vertical")

            """
            for i in range(len(scraping_bboxes)):
                with open("temp%s%d" % (city, i), "w") as f:
                    f.write(bbox_to_geojson(scraping_bboxes[i]))
            with open("temp%s%d" % (city, len(scraping_bboxes) + 1), "w") as f:
                f.write(bbox_to_geojson(row))
            """

            scrape_name = "%s_%s_perimeter_%dm" % (
                datetime.datetime.now().strftime("%Y-%m-%d"),
                city,
                radius_meters
            )
            scraper = gmaps_scraper.scrapers.PlacesNearbyScraper(
                api_key = API_KEY,
                output_directory_name = scrape_name,
                writer = "mongo"
            )
            for bbox in scraping_bboxes:
                scraper.scrape_subdivisions(
                    grid_width = 3,
                    query = "",
                    **bbox
                )
