#!/usr/bin/python

## Library Imports #############################################################
#from geopy.geocoders import GoogleV3
import glob
import os

import parse_tiger # Separate Python script used to get city extents

api_key = "AIzaSyAUW95lWu8QlrA8344BqDnkJm5CQkSYRNw"
state_input = "none"

## Main Function ###############################################################
def find_subdivision(subdivision_id_array, current_extents, grid_width):
    #https://maps.googleapis.com/maps/api/staticmap?center=40.750492,%20-73.980554&zoom=15&size=600x600&maptype=roadmap&key=AIzaSyAUW95lWu8QlrA8344BqDnkJm5CQkSYRNw&style=feature:poi|color:0xff0000|element:geometry.stroke
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
    if (len(subdivision_id_array) >= 1):
        print(subdivision_id_array[0])
        if (subdivision_id_array[0] != "root"):

            current_grid_number = int(subdivision_id_array[0])
            grid_x = ((current_grid_number - 1) % grid_width)
            grid_y = ((current_grid_number - 1) / grid_width)
            extent_width = current_extents["max_longitude"] - current_extents["min_longitude"]
            extent_height = current_extents["max_latitude"] - current_extents["min_latitude"]

            current_extents["min_longitude"] += extent_width / grid_width * grid_y
            current_extents["min_latitude"] += extent_height / grid_width * grid_x
            current_extents["max_longitude"] = current_extents["min_longitude"] + (extent_width / grid_width)
            current_extents["max_latitude"] = current_extents["min_latitude"] + (extent_height / grid_width)

        return find_subdivision(subdivision_id_array[1:], current_extents,
                                grid_width)
    else:
        print("finished")
        return current_extents




while (not os.path.isdir("tiger-2016/" + state_input)):
    state_input = raw_input("Please specify a state: ")
state_shapefile = glob.glob("tiger-2016/" + state_input + "/*.shp")[0]

## Program Initialization ######################################################
# Prompt the user to enter a city
city_extents = False
while (not city_extents):
    city_input = raw_input("Please specify a city or \"full\" for the entire "
                           + "state: ")
    city_extents = parse_tiger.get_extents(state_shapefile, city_input)

print("ORIGINAL: %s" % city_extents)
print(find_subdivision("root -> 5 -> 8 -> 2 -> 7 -> 3 -> 2 -> 8 -> 6 -> 9".split(" -> "), city_extents, 3))
