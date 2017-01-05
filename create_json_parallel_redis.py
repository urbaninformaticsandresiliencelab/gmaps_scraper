#!/usr/bin/python
# Merge and deduplicate data, writing the result as a JSON, using Redis as the
# shared memory store.

import glob
import json
import multiprocessing
import os
import pickle
import sys
import time

import redis

PICKLE_DIRECTORY = "output/raw_pickle/" # Where to look for pickles

JSON_DIRECTORY = "output/json/" # Where to save JSON files

THREADS = 4 # More THREADS also use more memory so be careful

COLOURS = {
    "red": "\033[91m",
    "blue": "\033[94m",
    "green": "\033[92m",
    "end": "\033[0m",
}

# Attempt to load the START_TIME constant stored in the database; if it does not
# exist, set it to the current time
place_id_db = redis.StrictRedis(host = "localhost", port = 6379, db = 0)
stored_START_TIME = place_id_db.get("START_TIME")
if (stored_START_TIME is None):
    START_TIME = time.time()
    place_id_db.set("START_TIME", START_TIME)
else:
    START_TIME = float(stored_START_TIME)

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

def process_pickle(pickle_path):
    """ Process a single pickle

    Process a pickle by iterating over its place objects and adding the ones
    whose place_ids don't yet exist in the database to the database.

    Args:
        pickle_path: A string containing the path to a pickle file.
    """

    pickle_object = open(pickle_path)

    # From https://stackoverflow.com/questions/12761991/how-to-use-append-with-pickle-in-python/12762056#12762056
    while True:
        try:
            for obj in pickle.load(pickle_object):
                place_id = obj["place_id"]
                if (place_id_db.get(place_id) is None):
                    place_id_db.set(place_id,
                                    json.dumps(obj, separators=(',',':')))

        except EOFError:
            break

    # %s is used instead of %d because redis returns strings
    update_progress("Merged", pickle_path.split("/")[2],
                    "Pickle %s of %s" % (place_id_db.incr("num_pickles_finished"),
                                         place_id_db.get("num_pickles")),
                    colour = "blue")

    pickle_object.close()

def create_json(scrape_path):
    """ Create a JSON file from a scrape

    Create a JSON by having n instances of process_pickle running at the same
    time on different pickle files. These processes all interact with the same
    Redis database where keys are the place_ids and values are the corresponding
    details for each place. When all instances have finished, the JSON is
    assembled by iterating over the values of keys in the database.

    Args:
        scrape_path: A string containing the path to a scrape's root directory.
    """

    scrape_path_basename = scrape_path.split("/")[2]
    pool = multiprocessing.Pool(THREADS)

    output_file = "%s/%s.json" % (JSON_DIRECTORY, scrape_path_basename)
    if (os.path.isfile(output_file)):
        update_progress("Skipped", scrape_path_basename, "Already exists",
                        colour = "blue")
        return
    update_progress("Started", scrape_path_basename, colour = "green")

    pickle_paths = glob.glob("%s/*/data.p" % scrape_path)
    pickle_paths += glob.glob("%s/data.p" % scrape_path)

    place_id_db.flushdb()
    place_id_db.set("num_pickles", len(pickle_paths))
    place_id_db.set("num_pickles_finished", 0)
    pool.map(process_pickle, pickle_paths)
    pool.close()
    pool.join()
    place_id_db.delete("START_TIME")
    place_id_db.delete("num_pickles")
    place_id_db.delete("num_pickles_finished")

    update_progress("Writing", scrape_path_basename, colour = "blue")
    output_file_object = open(output_file, "w")
    output_file_object.write("[")

    first_line = True
    for key in place_id_db.scan_iter():
        if (first_line):
            output_file_object.write("\n    %s" % place_id_db.get(key))
            first_line = False
        else:
            output_file_object.write(",\n    %s" % place_id_db.get(key))

    output_file_object.write("\n]")
    output_file_object.close()
    update_progress("Finished", scrape_path_basename, colour = "green")

if (__name__ == "__main__"):
    if (not os.path.isdir(JSON_DIRECTORY)):
        os.makedirs(JSON_DIRECTORY)

    print("Available scrapes:")
    print("\n".join(glob.glob("%s/*" % PICKLE_DIRECTORY)))
    scrape_path = "null"
    while (not os.path.isdir(scrape_path)):
        scrape_path = raw_input("Please choose a scrape to process: ")

    print("  TIME    STATUS                                                        LABEL INFO")
    create_json(scrape_path)
