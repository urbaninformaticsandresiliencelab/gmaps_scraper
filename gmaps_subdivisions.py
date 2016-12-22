#!/usr/bin/env python

## Library Imports #############################################################
#from geopy.geocoders import GoogleV3
from math import radians, cos, sin, asin, sqrt
import cPickle as pickle
import datetime
import googlemaps
import glob
#import numpy
import os
import time
import sys

import parse_tiger # Separate Python script used to get city extents

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
place_types = ["accounting","airport","amusement_park","aquarium","art_gallery","atm","bakery","bank","bar","beauty_salon","bicycle_store","book_store","bowling_alley","bus_station","cafe","campground","car_dealer","car_rental","car_repair","car_wash","casino","cemetery","church","city_hall","clothing_store","convenience_store","courthouse","dentist","department_store","doctor","electrician","electronics_store","embassy","establishment","finance","fire_station","florist","food","funeral_home","furniture_store","gas_station","general_contractor","grocery_or_supermarket","gym","hair_care","hardware_store","health","hindu_temple","home_goods_store","hospital","insurance_agency","jewelry_store","laundry","lawyer","library","liquor_store","local_government_office","locksmith","lodging","meal_delivery","meal_takeaway","mosque","movie_rental","movie_theater","moving_company","museum","night_club","painter","park","parking","pet_store","pharmacy","physiotherapist","place_of_worship","plumber","police","post_office","real_estate_agency","restaurant","roofing_contractor","rv_park","school","shoe_store","shopping_mall","spa","stadium","storage","store","subway_station","synagogue","taxi_stand","train_station","transit_station","travel_agency","university","veterinary_care","zoo"]

# From https://developers.google.com/places/web-service/search: The maximum
# allowed radius is 50000 meters.
max_radius_meters = 50000

# No further subdivisions under this size will be made
min_radius_meters = 5

# The length of a period, in seconds
period_length = 60*60 # 60*60 = one hour

# Maximum number of requests that can be made in one period
max_requests_per_period = 5000

# Time, in seconds, to sleep between each request
request_delay = 1.5

# Maximum number of times a request can be retried
max_retries = 5

## Variables Used Internally ###################################################
# Google Maps API client object
gmaps = googlemaps.Client(
            key = api_key,
            timeout = 600
        )

# Used during interactive input (changed later)
city_input = "null"
state_input = "null"

# Files that will be written to (names are changed later)
output_directory_root = "output/raw_pickle/" # The top level output directory
output_directory = "data" # The subdirectory that results will be written to

# Used for self-imposed request limiting
start_time = time.time()
request_period_start_time = time.time()
pages_traversed = 0
pages_traversed_this_period = 0

## Utility Functions ###########################################################
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

# Initialize output directory
def initialize_output_directory(directory_name):
    global output_directory
    output_directory = output_directory_root + "/" + directory_name
    if (not os.path.exists(output_directory)):
        os.makedirs(output_directory)
    else:
        print("Error: directory already exists")
        raise Exception
    print("Writing data and logs to %s/" % output_directory)
    log("request_log.csv", "TIME,REQUESTS")
    log("error_log.csv", "TIME,ERROR")
    log("warning_log.csv", "TIME,ERROR")

# Append to a log
def log(filename, message):
        file_object = open(output_directory + "/" + filename, "a")
        file_object.write(message + "\n")
        file_object.close()

## Main Function ###############################################################
# Get points of interest from the Google Maps API, given a latitude, longitude,
# radius, and place type. The page argument is used internally to track the
# recursion layers and the token argument is also used internally to pass tokens
# to the next recursion.

# Returns an array of points of interest

def get_points_of_interest(latitude, longitude, radius_meters, place_type,
                           subdivision_id_string,
                           page = 1, retries = 0, token = "none"):

    global pages_traversed
    global pages_traversed_this_period
    global request_period_start_time
    combined_results = []

    # Self-imposed rate limiting by using a loop
    while (((time.time() - request_period_start_time) < period_length)
           and (pages_traversed_this_period >= max_requests_per_period)):

        print("Max requests per period reached. %f Seconds until next period."
              % (period_length - (time.time() - request_period_start_time)))
        time.sleep(10)

    # End of period
    if ((time.time() - request_period_start_time) >= period_length):

        # Reset variables
        request_period_start_time = time.time()
        pages_traversed_this_period = 0

        # For analysis: output time since program started and total requests
        # made during this period
        log(
            "request_log.csv",
            ("%f,%d" % ((time.time() - start_time), pages_traversed))
        )

        # Create a new output directory
        initialize_output_directory((
            "%s_%s_%s" % (
                city_input, state_input, datetime.datetime.now().isoformat()
            )
        ).replace(" ", "_"))

    print("Retrieving page %d" % page)

    # Increment the counters
    pages_traversed += 1
    pages_traversed_this_period += 1

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
        # "A next_page_token will not be returned if there are no additional
        # results to display." If the next_page_token exists, recurse and append
        # to the combined_results array.
        time.sleep(request_delay)
        if "next_page_token" in results:
            token = results["next_page_token"]
            combined_results += get_points_of_interest(latitude, longitude,
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
        log(
            "error_log.csv",
            ("%f,%s" % ((time.time() - start_time), err))
        )

        time.sleep(request_delay)

        # Retry
        if (retries <= max_retries):
            print("Retrying (attempt #%d)" % (retries + 1))
            combined_results += get_points_of_interest(latitude, longitude,
                                                       radius_meters,
                                                       place_type,
                                                       subdivision_id_string,
                                                       page, retries + 1, token)
        else:
            print("Max retries exceeded; skipping this subdivision.")
            log(
                "warning_log.csv",
                ("%f,%s. Subdivision ID: %s. Place type: %s. Coordinates: (%f, %f). Radius: %f" % (
                    (time.time() - start_time),
                    "Maximum number of retries exceeded",
                    subdivision_id_string,
                    place_type,
                    latitude,
                    longitude,
                    radius_meters)
                )
            )

        pass

    # Return the combined results
    return combined_results

'''
################################################################################
# This is my old algorithm. It basically divide the entire city into small grid
# and loop through.

# Below the values are the boundaries for NYC. Keep them or change them to
# Boston's boundary
# To find the boundaries, go to google maps, put a city in the search box, and
# the boundary will show up. You can roughly get the boundaries.
# The boundaries do not have to be too accurate, but make sure they cover the
# entire city
# lat: 40.91 to 40.49
# lon: -74.26 to -73.69

lat_limits = list(numpy.arange(40.75, 40.751, 0.002))
lon_limits = list(numpy.arange(-74.00, -73.96, 0.002))

# loop over types, latitudes, and longitudes.
for place_type in place_types:
    for lat_limit in lat_limits:
        for lon_limit in lon_limits:
                # for each pair of latitude and longitude, find the places within
                # 200 meter radius.
                results = get_points_of_interest(lat_limit, lon_limit, 200,
                                                 place_type)
                print lat_limit, lon_limit, place_type, len(results)
                print("%s pages traversed" % pages_traversed)

                # save the results in a pickle file.
                filename = open("NYC_new.p", "a+b")
                pickle.dump(results, filename)
                filename.close()
'''

################################################################################
def extract_subdivisions(min_latitude, max_latitude, min_longitude,
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
            ## MATH PART #######################################################
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
            # ancestry. To find exactly where on a grid this subdivision lies,
            # use the above table.
            subdivision_id += 1
            subdivision_id_string = (subdivision_parent_id + " -> "
                                     + str(subdivision_id))

            if (target_subdivision != 0):
                if (target_subdivision == subdivision_id):
                    print("Skipped to %s" % subdivision_id_string)
                else:
                    continue

            # First, we need to establish the bounds of this subdivision
            subdivision_min_latitude = (min_latitude
                                        + (subdivision_height * float(column)))
            subdivision_max_latitude = (subdivision_min_latitude
                                        + subdivision_height)
            subdivision_min_longitude = (min_longitude
                                         + (subdivision_width * float(row)))
            subdivision_max_longitude = (subdivision_min_longitude
                                        + subdivision_height)
            #print("Bottom left coords: (%f, %f)" % (subdivision_min_latitude,
            #                                        subdivision_min_longitude))
            #print("Top right coords: (%f, %f)" % (subdivision_max_latitude,
            #                                      subdivision_max_longitude))

            # Then, we can establish the center and the radius of the circle
            # needed to encompass the entire subdivision
            subdivision_center_longitude = ((subdivision_min_longitude
                                             + subdivision_max_longitude)/2)
            subdivision_center_latitude = ((subdivision_min_latitude
                                             + subdivision_max_latitude)/2)

            # The haversine formula is used to convert the width and height
            # from degrees into meters before finding the radius in meters
            width_meters = haversine(0, subdivision_min_longitude,
                                     0, subdivision_max_longitude)
            height_meters = haversine(0, subdivision_min_latitude,
                                      0, subdivision_max_latitude)

            # From there, we use the pythagorean theorem to find the radius
            subdivision_radius_meters = (sqrt((width_meters/2)**2
                                              + (height_meters/2)**2))

            ## API PART ########################################################
            # This bool will be changed to true if more recursions are necessary
            make_subdivisions = False

            if (len(split_id) == 0) or ("" in split_id):
                print("Subdivision ID: %s" % subdivision_id_string)
                print("Center coords: (%f, %f)" % (subdivision_center_latitude,
                                                   subdivision_center_longitude))
                print("Radius: %f meters" % subdivision_radius_meters)

                # If the radius of the subdivision exceeds the max, skip the result
                # collection and recurse
                if (subdivision_radius_meters > max_radius_meters):
                    print("Making subdivisions because radius exceeded maximum")
                    make_subdivisions = True

                elif (subdivision_radius_meters < min_radius_meters):
                    print("Terminating branch because radius is below the minimum")
                    log(
                        "warning_log.csv",
                        ("%f,%s. Subdivision ID: %s. Place type: %s. Coordinates: (%f, %f). Radius: %f" % (
                            (time.time() - start_time),
                            "Radius fell below minimum value",
                            subdivision_id_string,
                            place_type,
                            subdivision_center_latitude,
                            subdivision_center_longitude,
                            subdivision_radius_meters)
                        )
                    )

                else:

                    # Get results
                    results = get_points_of_interest(subdivision_center_latitude,
                                                     subdivision_center_longitude,
                                                     subdivision_radius_meters,
                                                     place_type,
                                                     subdivision_id_string)
                    print("%d results for place_type %s" % (len(results),
                                                            place_type))
                    print("%d pages traversed since program was started"
                          % pages_traversed)

                    # Save the results in a pickle file
                    filename = open(output_directory + "/data.p", "a+b")
                    print(results)
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
                extract_subdivisions(subdivision_min_latitude,
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

    initialize_output_directory((
        "%s_%s_%s" % (
            city_input, state_input, datetime.datetime.now().isoformat()
        )
    ).replace(" ", "_"))

    print

    # For each place_type, the subdivision -> extraction process is restarted
    # from scratch.
    for place_type in place_types:
        extract_subdivisions(city_extents["min_latitude"],
                             city_extents["max_latitude"],
                             city_extents["min_longitude"],
                             city_extents["max_longitude"],
                             3, place_type)
