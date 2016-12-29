#!/usr/bin/python
# Merge and deduplicate data, writing the result as a JSON

import glob
import json
import multiprocessing
import os
import pickle
import subprocess
import sys
import time


PICKLE_DIRECTORY = "output/raw_pickle/" # Where to look for pickles

JSON_DIRECTORY = "output/json/" # Where to save JSON files

ARCHIVE_DIRECTORY = "output/archive/" # Where to save compressed archives

TAR_PATH = "/usr/bin/tar" # The path to the tar binary

MIN_UPDATE_INTERVAL = 60 # Actual interval may be slightly longer than this

THREADS = 3 # More THREADS also use more memory so be careful

START_TIME = time.time()
COLOURS = {
    "red": "\033[91m",
    "blue": "\033[94m",
    "green": "\033[92m",
    "end": "\033[0m",
}

def update_progress(status, main_label, secondary_label = "", colour = "white"):
    """ Write progress to STDOUT

    For logging purposes: pretty printing of program and worker process status

    Args:
        status: A string describing the overall status, such as "Finished",
            "Skipped", or "90%". This appears in the first column and can be
            coloured.
        main_label: A string containing the label of the job. This appears in
            the second column.
        secondary_label: A string containing information to accompany the
            main_label, such as "currently processing #x of y".
        colour: A string containing an index of the COLOURS table which the
            status will be coloured to.
    """

    colour_start = ""
    colour_end = ""
    if (colour != "white") and (colour in COLOURS):
        colour_start = COLOURS[colour]
        colour_end = COLOURS["end"]

    timestamp = time.time() - START_TIME
    if (type(status) is float):
        print("%6d %s%8.3f%%%s %60s %s" % (timestamp, colour_start, status,
                                           colour_end, main_label,
                                           secondary_label))
    else:
        print("%6d %s%9s%s %60s %s" % (timestamp, colour_start, status,
                                       colour_end, main_label, secondary_label))

def archive(scrape_path):
    """ Compressed pickled data.

    Args:
        scrape_path: A string containing the path to a directory containing
            pickled data.
    """
    scrape_path_basename = scrape_path.split("/")[-1]
    output_file = "%s/%s.tar.xz" % (ARCHIVE_DIRECTORY, scrape_path_basename)
    if (os.path.isfile(output_file)):
        update_progress("Skipped", scrape_path_basename, "Archive: Already exists",
                        colour = "blue")
        return
    update_progress("Started", scrape_path_basename, "Archive", colour = "green")

    if (os.path.isfile(TAR_PATH)):
        return_code = subprocess.call(["tar", "-Jcf", output_file, scrape_path])
        if (return_code == 0):
            update_progress("Finished", scrape_path_basename, "Archive", colour = "green")
        else:
            update_progress("Failed", scrape_path_basename, "Archive", colour = "red")
            subprocess.call(["rm", "-rf", output_file])
    else:
        update_progress(
            "Failed", scrape_path_basename,
            "Archive: %s does not exist" % TAR_PATH, colour = "red"
        )

def create_json(scrape_path):
    """ Merge and deduplicate pickled data and write the data to a JSON file

    Args:
        scrape_path: A string containing the path to a directory containing
            pickled data.
    """

    scrape_path_basename = scrape_path.split("/")[-1]
    seen_place_ids = []
    data = []

    output_file = "%s/%s.json" % (JSON_DIRECTORY, scrape_path_basename)
    if (os.path.isfile(output_file)):
        update_progress("Skipped", scrape_path_basename, "JSON: Already exists",
                        colour = "blue")
        return
    update_progress("Started", scrape_path_basename, "JSON: Creating", colour = "green")

    # Look for "data.p" files in subdirectories and the root directory
    data_pickles = glob.glob("%s/*/data.p" % scrape_path)
    data_pickles += glob.glob("%s/data.p" % scrape_path)

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
                            scrape_path_basename,
                            "JSON: pickle %2d of %2d" % (data_pickles_progress,
                                                   len(data_pickles))
                        )
                        last_update = current_time
            except EOFError:
                seek_since_last_pickle += os.path.getsize(data_pickle)
                break
        data_pickle_object.close()

    # Write the merged and deduplicated data as a JSON
    update_progress("Writing", scrape_path_basename, "JSON", colour = "blue")
    output_file_object = open(output_file, "w")
    json.dump(data, output_file_object, indent = 4, separators=(',', ': '))
    output_file_object.close()
    update_progress("Finished", scrape_path_basename, "JSON", colour = "green")

def process(scrape_path):
    create_json(scrape_path)
    archive(scrape_path)

if (__name__ == "__main__"):
    scrape_paths = []
    pool = multiprocessing.Pool(THREADS)

    if (not os.path.isdir(JSON_DIRECTORY)):
        os.makedirs(JSON_DIRECTORY)

    if (not os.path.isdir(ARCHIVE_DIRECTORY)):
        os.makedirs(ARCHIVE_DIRECTORY)

    for scrape_path in glob.glob("%s/*" % PICKLE_DIRECTORY):
        if os.path.isdir(scrape_path):
            scrape_paths.append(scrape_path)

    print("  TIME    STATUS                                                        LABEL INFO")
    pool.map(process, scrape_paths)
    pool.close()
    pool.join()
