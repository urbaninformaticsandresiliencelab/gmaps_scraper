#!/usr/bin/python
# Merge and deduplicate data, writing the result as a JSON

## Library Imports #############################################################
import glob
import json
import multiprocessing
import os
import pickle
import sys
import time

## Configuration ###############################################################

PICKLE_DIRECTORY = "output/raw_pickle/" # Where to look for pickles

JSON_DIRECTORY = "output/json/" # Where to save JSON files

MIN_UPDATE_INTERVAL = 60 # Actual interval may be slightly longer than this

THREADS = 3 # More THREADS also use more memory so be careful

## Variables Used Internally ###################################################
# Used for logging
START_TIME = time.time()
COLOURS = {
    "red": "\033[91m",
    "blue": "\033[94m",
    "green": "\033[92m",
    "end": "\033[0m",
}

## Main Functions ##############################################################
# For logging purposes: pretty printing of program and worker processes' status
def update_progress(status, main_label, secondary_label = "", colour = "white"):
    colour_start = ""
    colour_end = ""
    if (colour != "white") and (colour in COLOURS):
        colour_start = COLOURS[colour]
        colour_end = COLOURS["end"]

    timestamp = time.time() - START_TIME
    if (type(status) is float):
        print("%6d %s%8.3f%%%s %55s %s" % (timestamp, colour_start, status,
                                           colour_end, main_label,
                                           secondary_label))
    else:
        print("%6d %s%9s%s %55s %s" % (timestamp, colour_start, status,
                                       colour_end, main_label, secondary_label))

# Main function to merge and deduplicate pickles generated by gmaps-subdivisions
def create_json(root_directory):
    root_directory_basename = root_directory.split("/")[-1]
    seen_place_ids = []
    data = []

    output_file = "%s/%s.json" % (JSON_DIRECTORY, root_directory_basename)
    if (os.path.isfile(output_file)):
        update_progress("Skipped", root_directory_basename, "already exists",
                        colour = "blue")
        return
    update_progress("Started", root_directory_basename, colour = "green")

    # Look for "data.p" files in subdirectories and the root directory
    data_pickles = glob.glob("%s/*/data.p" % root_directory)
    data_pickles += glob.glob("%s/data.p" % root_directory)

    # For logging purposes
    data_pickles_progress = 0
    last_update = time.time()
    seek_since_last_pickle = 0
    total_size = 0
    for data_pickle in data_pickles:
        total_size += os.path.getsize(data_pickle)

    # Iterate over pickles in the scrape
    for data_pickle in data_pickles:
        data_pickle_object = open(data_pickle)
        data_pickles_progress += 1

        # From https://stackoverflow.com/questions/12761991/how-to-use-append-with-pickle-in-python/12762056#12762056
        while True:
            try:
                for obj in pickle.load(data_pickle_object):
                    # Ignore duplicate places
                    if (not obj["place_id"] in seen_place_ids):
                        seen_place_ids.append(obj["place_id"])
                        data.append(obj)

                    # Logging
                    current_time = time.time()
                    if (current_time - last_update > MIN_UPDATE_INTERVAL):
                        update_progress(
                            float(seek_since_last_pickle + data_pickle_object.tell())/total_size*100,
                            root_directory_basename,
                            "pickle %2d of %2d" % (data_pickles_progress,
                                                   len(data_pickles))
                        )
                        last_update = current_time
            except EOFError:
                seek_since_last_pickle += os.path.getsize(data_pickle)
                break
        data_pickle_object.close()

    # Write the merged and deduplicated data as a JSON
    update_progress("Writing", root_directory_basename, colour = "blue")
    output_file_object = open(output_file, "w")
    json.dump(data, output_file_object, indent = 4, separators=(',', ': '))
    output_file_object.close()
    update_progress("Finished", root_directory_basename, colour = "green")

## Start Converting ############################################################
if (__name__ == "__main__"):
    root_directories = []
    pool = multiprocessing.Pool(THREADS)

    for root_directory in glob.glob("%s/*" % PICKLE_DIRECTORY):
        if os.path.isdir(root_directory):
            root_directories.append(root_directory)

    print("  TIME    STATUS                                                   LABEL INFO")
    pool.map(create_json, root_directories)
    pool.close()
    pool.join()
