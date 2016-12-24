#!/usr/bin/env python

## Library Imports #############################################################
#from geopy.geocoders import GoogleV3
from math import radians, cos, sin, asin, sqrt
import cPickle as pickle
import googlemaps
import glob
#import numpy
import os
import time
import sys

import parse_tiger
import geo
import visualizer

## Configuration ###############################################################
# Attempt to load credentials
try:
    import credentials
    if (credentials.api_key == "Enter key here"):
        print("Error: no api key provided. Please add one to credentials.py.")
        sys.exit(1)
except:
    if (not os.path.isfile("credentials.py")):
        print("Error: could not find credentials.py. One has been created for you.")
    credentials_file = open("credentials.py", "w")
    credentials_file.write("# Google maps API key to be used by the scraper\n"
                           "api_key = \"Enter key here\"\n")
    credentials_file.close()
    sys.exit(1)
api_key = credentials.api_key

# There are 96 types of places that can be acquired
PLACE_TYPES = ["accounting","airport","amusement_park","aquarium","art_gallery","atm","bakery","bank","bar","beauty_salon","bicycle_store","book_store","bowling_alley","bus_station","cafe","campground","car_dealer","car_rental","car_repair","car_wash","casino","cemetery","church","city_hall","clothing_store","convenience_store","courthouse","dentist","department_store","doctor","electrician","electronics_store","embassy","establishment","finance","fire_station","florist","food","funeral_home","furniture_store","gas_station","general_contractor","grocery_or_supermarket","gym","hair_care","hardware_store","health","hindu_temple","home_goods_store","hospital","insurance_agency","jewelry_store","laundry","lawyer","library","liquor_store","local_government_office","locksmith","lodging","meal_delivery","meal_takeaway","mosque","movie_rental","movie_theater","moving_company","museum","night_club","painter","park","parking","pet_store","pharmacy","physiotherapist","place_of_worship","plumber","police","post_office","real_estate_agency","restaurant","roofing_contractor","rv_park","school","shoe_store","shopping_mall","spa","stadium","storage","store","subway_station","synagogue","taxi_stand","train_station","transit_station","travel_agency","university","veterinary_care","zoo"]

# From https://developers.google.com/places/web-service/search: The maximum
# allowed radius is 50000 meters.
MAX_RADIUS_METERS = 50000

# No further subdivisions under this size will be made
MIN_RADIUS_METERS = 5

# The length of a period, in seconds
PERIOD_LENGTH = 60*60 # One hour

# Maximum number of requests that can be made in one period
MAX_REQUESTS_PER_PERIOD = 5000

# Time, in seconds, to sleep between each request
REQUEST_DELAY = 1.5

# Maximum number of times a request can be retried
MAX_RETRIES = 5

# Files that will be written to (names are changed later)
OUTPUT_DIRECTORY_ROOT = "output/raw_pickle/" # The top level output directory

## Variables Used Internally ###################################################
# Google Maps API client object
gmaps = googlemaps.Client(
    key = api_key,
    timeout = 600
)

# Used during interactive input (changed later)
city_input = "null"
state_input = "null"

class Scraper(object):

    def __init__(self, output_directory_root):
        # The subdirectory that results will be written to (changed by the
        # intialize_output_directory function later)
        if (len(output_directory_root) == 0):
            self.output_directory_root = "Untitled_Scrape"
        else:
            self.output_directory_root = output_directory_root
        self.output_directory = ""

        # Used for logging
        self.start_time = time.time()

        # Used for self-imposed request limiting
        self.request_period_start_time = time.time()
        self.traversed = 0
        self.traversed_this_period = 0

        self.initialize_output_directory()

    # Initialize output directory
    def initialize_output_directory(self):
        self.output_directory = "%s/%s" % (
            self.output_directory_root, time.strftime("%Y-%m-%dT%H:%M:%S")
        )
        os.makedirs(self.output_directory)

        print("Writing data and logs to %s/" % self.output_directory)

        # Initialize logs
        logs = {
            "request_log.csv": "REQUESTS",
            "error_log.csv": "ERROR",
            "termination_log.csv": "REASON"
        }
        for log in logs.iterkeys():
            _file = open("%s/%s" % (self.output_directory, log), "w")
            _file.write("TIME,%s\n" % logs[log])
            _file.close()

    # Append to a log
    def log(self, filename, message):
            _file = open("%s/%s" % (self.output_directory, filename), "a")
            _file.write("%f,%s\n" % (time.time() - self.start_time, message))
            _file.close()

    # Get points of interest from the Google Maps API, given a latitude,
    # longitude, radius, and place type. The page argument is used internally to
    # track the recursion layers and the token argument is also used internally
    # to pass tokens to the next recursion.
    # Returns an array of points of interest
    def scrape_places_nearby(self, latitude, longitude, radius_meters,
                             place_type, subdivision_id_string,
                             page = 1, retries = 0, token = "none"):

        combined_results = []

        # Self-imposed rate limiting ###########################################
        while (((time.time() - self.request_period_start_time) < PERIOD_LENGTH)
               and (self.traversed_this_period >= MAX_REQUESTS_PER_PERIOD)):

            print("Max requests per period reached. %f Seconds until next period."
                  % (PERIOD_LENGTH - (time.time() - self.request_period_start_time)))
            time.sleep(10)

        # End of period
        if ((time.time() - self.request_period_start_time) >= PERIOD_LENGTH):

            # Reset variables
            self.request_period_start_time = time.time()
            self.traversed_this_period = 0

            # For analysis: output time since program started and total requests
            # made during this period
            self.log("request_log.csv", self.traversed)

            # Create a new output directory
            self.initialize_output_directory()

        # Scraping #############################################################
        print("Retrieving page %d" % page)

        # Increment the counters
        self.traversed += 1
        self.traversed_this_period += 1

        try:
            # Only provide a page_token if the next_page_token was provided
            if (token == "none"):
                results = gmaps.places_nearby(
                    location = {
                        "lat": latitude,
                        "lng": longitude
                    },
                    radius = radius_meters,
                    type = place_type
                )
            else:
                results = gmaps.places_nearby(
                    location = {
                        "lat": latitude,
                        "lng": longitude
                    },
                    radius = radius_meters,
                    type = place_type,
                    page_token = token
                )

            # From https://developers.google.com/places/web-service/search:
            # results to display." If the next_page_token exists, recurse and append
            # to the combined_results array.
            time.sleep(REQUEST_DELAY)
            if "next_page_token" in results:
                token = results["next_page_token"]
                combined_results += self.scrape_places_nearby(latitude, longitude,
                                                              radius_meters,
                                                              place_type,
                                                              subdivision_id_string,
                                                              page + 1, retries,
                                                              token)

            # Append the results list
            combined_results += results["results"]

        except Exception as err:
            print("Error: %s" % err)
            # For analysis: output time since program started and the text of the
            # error
            self.log("error_log.csv", err)

            time.sleep(REQUEST_DELAY)

            # Retry
            if (retries <= MAX_RETRIES):
                print("Retrying (attempt #%d)" % (retries + 1))
                combined_results += self.scrape_places_nearby(latitude, longitude,
                                                              radius_meters,
                                                              place_type,
                                                              subdivision_id_string,
                                                              page, retries + 1, token)
            else:
                print("Max retries exceeded; skipping this subdivision.")
                self.log(
                    "termination_log.csv",
                    ("Maximum number of retries exceeded. Subdivision ID: %s. Place type: %s. Coordinates: (%f, %f). Radius: %f" % (
                        subdivision_id_string,
                        place_type,
                        latitude,
                        longitude,
                        radius_meters
                    ))
                )

            pass

        # Return the combined results
        return combined_results

    def extract_subdivisions(self, min_latitude, max_latitude, min_longitude,
                             max_longitude, grid_width, place_type,
                             subdivision_parent_id = "root",
                             target_subdivision_id = ""):

        subdivision_id = 0
        subdivision_width = (max_latitude - min_latitude)/grid_width
        subdivision_height = (max_longitude - min_longitude)/grid_width

        # If a target subdivision ID is supplied, skip to that subdivision
        target_subdivision = 0
        split_id = target_subdivision_id.split(" -> ")
        if (target_subdivision_id != ""):
            if (target_subdivision_id[:4] == "root"):
                print("Skipping forward to %s\n" % target_subdivision_id)
                target_subdivision = int(split_id[1])
                split_id = split_id[2:]
            else:
                target_subdivision = int(split_id[0])
                split_id = split_id[1:]
        target_subdivision_id = " -> ".join(split_id)

        for row in range(grid_width):
            for column in range(grid_width):
                ## MATH PART ###################################################
                # For example, a 3x3 grid of subdivisions with min_lat = 0,
                # min_long = 0, max_lat = 3, max_long = 3 would look like this:
                #
                # lat
                # ^
                # 3 +---+---+---+
                #   | 7 | 8 | 9 |
                # 2 +---+---+---+
                #   | 4 | 5 | 6 |
                # 1 +---+---+---+
                #   | 1 | 2 | 3 |
                # 0 +---+---+---+
                #   0   1   2   3 >long
                #
                # where the number inside each box corresponds to the order in
                # which that box is processed

                # The subdivision ID is used to track the current subdivision's
                # ancestry. To find exactly where on a grid this subdivision
                # lies, use the above table.
                subdivision_id += 1
                subdivision_id_string = (subdivision_parent_id + " -> "
                                         + str(subdivision_id))

                # If a target subdivision is specified, skip all of the below
                # logic and continue to the next loop
                if (target_subdivision != 0):
                    if (target_subdivision == subdivision_id):
                        print("Skipped to %s" % subdivision_id_string)
                    else:
                        continue

                # First, we need to establish the bounds of this subdivision
                subdivision_min_latitude = (min_latitude
                                            + (subdivision_width * float(row)))
                subdivision_max_latitude = (subdivision_min_latitude
                                            + subdivision_width)
                subdivision_min_longitude = (min_longitude
                                             + (subdivision_height * float(column)))
                subdivision_max_longitude = (subdivision_min_longitude
                                            + subdivision_height)

                # Then, we can establish the center and the radius of the circle
                # needed to encompass the entire subdivision
                subdivision_center_longitude = ((subdivision_min_longitude
                                                 + subdivision_max_longitude)/2)
                subdivision_center_latitude = ((subdivision_min_latitude
                                                 + subdivision_max_latitude)/2)

                # The haversine formula is used to convert the width and height
                # from degrees into meters before finding the radius in meters
                width_meters = geo.haversine(0, subdivision_min_longitude,
                                             0, subdivision_max_longitude)
                height_meters = geo.haversine(0, subdivision_min_latitude,
                                              0, subdivision_max_latitude)

                # From there, we use the pythagorean theorem to find the radius
                subdivision_radius_meters = (sqrt((width_meters/2)**2
                                                  + (height_meters/2)**2))

                ## API PART ####################################################
                # This bool will be changed to true if more recursions are
                # necessary
                make_subdivisions = False

                if (len(split_id) == 0) or ("" in split_id):
                    print("Subdivision ID: %s" % subdivision_id_string)
                    print("Center coords: (%f, %f)" % (subdivision_center_latitude,
                                                       subdivision_center_longitude))
                    print("Radius: %f meters" % subdivision_radius_meters)
                    print("Extents: ")
                    print({
                        "min_longitude": subdivision_min_longitude,
                        "max_longitude": subdivision_max_longitude,
                        "min_latitude": subdivision_min_latitude,
                        "max_latitude": subdivision_max_latitude
                    })
                    visualizer.add_points([
                        (subdivision_min_longitude, subdivision_min_latitude),
                        (subdivision_max_longitude, subdivision_min_latitude),
                        (subdivision_max_longitude, subdivision_max_latitude),
                        (subdivision_min_longitude, subdivision_max_latitude),
                        (subdivision_min_longitude, subdivision_min_latitude),
                    ])
                    print("Visualization: %s" % visualizer.generate_url())
                    visualizer.reset_points()

                    # If the radius of the subdivision exceeds the max, skip the result
                    # collection and recurse
                    if (subdivision_radius_meters > MAX_RADIUS_METERS):
                        print("Making subdivisions because radius exceeded maximum")
                        make_subdivisions = True

                    elif (subdivision_radius_meters < MIN_RADIUS_METERS):
                        print("Terminating branch because radius is below the minimum")
                        self.log(
                            "termination_log.csv",
                            ("Radius fell below minimum value. Subdivision ID: %s. Place type: %s. Coordinates: (%f, %f). Radius: %f" % (
                                subdivision_id_string,
                                place_type,
                                subdivision_center_latitude,
                                subdivision_center_longitude,
                                subdivision_radius_meters)
                            )
                        )

                    else:

                        # Get results
                        results = self.scrape_places_nearby(subdivision_center_latitude,
                                                            subdivision_center_longitude,
                                                            subdivision_radius_meters,
                                                            place_type,
                                                            subdivision_id_string)
                        print("%d results for place_type %s" % (len(results),
                                                                place_type))
                        print("%d pages traversed since program was started"
                              % self.traversed)

                        # Save the results in a pickle file
                        filename = open(self.output_directory + "/data.p", "a+b")
                        pickle.dump(results, filename)
                        filename.close()

                        # If 60 results were returned, recurse
                        if (len(results) == 60):
                            print("Making subdivisions because max results were "
                                  + "returned")
                            make_subdivisions = True

                else:
                    make_subdivisions = True

                # Recurse if necessary
                if (make_subdivisions):
                    print
                    self.extract_subdivisions(subdivision_min_latitude,
                                              subdivision_max_latitude,
                                              subdivision_min_longitude,
                                              subdivision_max_longitude,
                                              3, place_type,
                                              subdivision_id_string,
                                              target_subdivision_id)
                else:
                    print("Branch terminated\n")

## Program Initialization ######################################################

if (__name__ == "__main__"):
    # Prompt the user to enter a state
    while (not os.path.isdir("tiger-2016/" + state_input)):
        state_input = raw_input("Please specify a state: ")
    state_shapefile = glob.glob("tiger-2016/" + state_input + "/*.shp")[0]

    # Prompt the user to enter a city
    city_extents = False
    while (not city_extents):
        city_input = raw_input("Please specify a city or \"full\" for the entire "
                               + "state: ")
        city_extents = parse_tiger.get_extents(state_shapefile, city_input)
    print(city_extents)

    scraper_output_directory_root = ("%s/%s_%s_%s" % (
                                        OUTPUT_DIRECTORY_ROOT,
                                        time.strftime("%Y-%m-%d"),
                                        city_input, state_input
                                    )).replace(" ", "_")
    new_scraper = Scraper(scraper_output_directory_root)

    print

    # For each place_type, the subdivision -> extraction process is restarted
    # from scratch.
    for place_type in PLACE_TYPES:
        new_scraper.extract_subdivisions(city_extents["min_latitude"],
                                        city_extents["max_latitude"],
                                        city_extents["min_longitude"],
                                        city_extents["max_longitude"],
                                        3, place_type)

    print("Finished scraping %s, %s" % (city_input, state_input))
