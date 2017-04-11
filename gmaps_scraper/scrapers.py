#!/usr/bin/env python

import googlemaps
import json
import math
import os
import shutil
import subprocess
import sys
import time

import parse_tiger
import geo
import gms_io
import staticmaps

# From https://developers.google.com/places/web-service/search: The maximum
# allowed radius is 50000 meters.
MAX_RADIUS_METERS = 50000

# No further subdivisions under this size will be made
MIN_RADIUS_METERS = 5

# The length of a period, in seconds
PERIOD_LENGTH = 60*60 # One hour

# Maximum number of requests that can be made in one period
MAX_REQUESTS_PER_PERIOD = 5000

# Default time to sleep between requests
REQUEST_DELAY = 1.5

# Maximum number of times a request can be retried
MAX_RETRIES = 5

# Files that will be written to (names are changed later)
OUTPUT_DIRECTORY_ROOT = "output/raw/" # The top level output directory

# Used by scrape_details
JSON_DIRECTORY = "output/json/" # The directory containing all of the JSONs

DEFAULT_WRITER = "json"

# Main scraper class contains functionality for initialization and setting of
# output directory, logging, and rate limiting
class Scraper(object):
    """ Main scraper class

    Contains functionality for initialization and management of the output
    directory, logging, and rate limiting. Rate limiting is done by defining
    periods of a fixed length and a maximum number of requests per period which
    can not be exceeded; the script sleeps until the next period if the limit
    is reached.

    The rate_limit method must be called once before every request and handles
    the rate limiting by tracking the number of requests and time since the
    current period started.

    Attributes:
        gmaps: A googlemaps.Client object.
        gsm: A staticmaps.Constructor object.
        writer: An writer object provided by the gms_io library. These are
            initialized by the initialize_writer method. Each writer has a dump
            function that dumps data, which is the first and only required
            argument, to a file, database, etc.
        output_directory_name: A string containing the base name of the root
            directory containing all output generated by the scraper.
        output_directory: A string containing the name of the subdirectory of
            OUTPUT_DIRECTORY_ROOT containing all data for this scrape.
        period_directory: A string containing the name of the subdirectory of
            output_directory containing all coutput generated by the scraper in
            the current scraping period.
        start_time: A float of the Unix time when the scraper was initialized.
        request_delay: A float of the time to sleep between requests
        request_period_start_time: A float of the Unix time when the current
            period was started.
        traversed: An integer indicating how many pages were traversed since the
            scraper started.
        traversed_this_period: An integer indicating how many pages were
            traversed since the current period was started.
    """

    def __init__(self, api_key, output_directory_name = "Untitled_Scrape",
                 writer = DEFAULT_WRITER, flush_writer = True,
                 flush_output_directory = False):
        """ Initializes Scraper class

        Performs necessary initialization before the scraper starts running,
        including recording the program start time and initializing an output
        directory.

        Args:
            api_key: A string containing the API key to initialize the
                googlemaps.Client object with.
            output_directory_name: A directory which is a subdivision of
                OUTPUT_DIRECTORY_ROOT where scraped data and logs will be
                stored.
            writer: A string containing information about which writer to use.
            flush_writer: A boolean describing whether or not the writer should
                be flushed when initialized.
            flush_output_directory: A boolean describing whether or not the
                output directory should be flushed when the scraper initializes.
        """

        self.gmaps = googlemaps.Client(
            key = api_key,
            timeout = 600
        )
        self.gsm = staticmaps.Constructor()

        self.writer_type = writer
        self.flush_writer = flush_writer

        self.output_directory_name = output_directory_name
        self.output_directory = "%s/%s" % (
            OUTPUT_DIRECTORY_ROOT,
            self.output_directory_name.replace("/", "_"),
        )
        if (os.path.isdir(self.output_directory)) and (flush_output_directory):
            print("Removing existing directory %s" % self.output_directory)
            shutil.rmtree(self.output_directory)
        self.period_directory = ""

        self.start_time = time.time()

        self.request_delay = REQUEST_DELAY
        self.request_period_start_time = time.time()
        self.traversed = 0
        self.traversed_this_period = 0

        self.initialize_output_directory()

    def initialize_writer(self):
        """ Initialize a writer to dump data

        Initializes a new writer object from one of the classes provided by the
        gms_io library. Each class should provide a dump function that takes one
        argument, which is the data to be dumped. Each class has different
        initialization arguments; see the comments in gms_io.py for more info.
        """

        # Initialize writer
        if (self.writer_type == "pickle"):
            self.writer = gms_io.PickleWriter(("%s/data.p"
                                               % self.period_directory))
            print("Using gms_io.PickleWriter")
        elif (self.writer_type == "mongo"):
            self.writer = gms_io.MongoWriter(self.output_directory_name)
            print("Using gms_io.MongoWriter")
        else:
            self.writer = gms_io.JSONWriter(
                ("%s/data.json" % self.output_directory),
            )
            print("Using gms_io.JSONWriter")

        # Initialize duplicate checker
        try:
            self.writer.duplicate_checker = gms_io.RedisDuplicateChecker(
                set_name = time.strftime("%Y-%m-%dT%H:%M:%S")
            )
        except Exception as err:
            print("Could not instance RedisDuplicateChecker object: %s" % err)
            print("Using SQLite3DuplicateChecker instead")
            self.writer.duplicate_checker = gms_io.SQLite3DuplicateChecker(
                db_path = "%s/seen_places.db" % self.output_directory
            )
        if (self.flush_writer):
            self.writer.duplicate_checker.flush()

    def initialize_output_directory(self):
        """ Initializes an output directory for the current period

        Creates a directory in which all data and logs generated by the scraper
        in the current period will be stored. The name of the directory is an
        ISO-formatted timestamp corresponding to when the period was started.

        Additionally, blank log files with headers are created.
        """
        self.period_directory = "%s/%s" % (
            self.output_directory,
            time.strftime("%Y-%m-%dT%H:%M:%S")
        )
        os.makedirs(self.period_directory)

        self.initialize_writer()

        print("Initialized new period directory %s/" % self.period_directory)

        # Initialize logs
        logs = {
            "request_log.csv": "REQUESTS",
            "error_log.csv": "ERROR",
            "termination_log.csv": "REASON"
        }
        for log in logs.iterkeys():
            log_path = "%s/%s" % (self.output_directory, log)
            if (not os.path.exists(log_path)):
                with open(log_path, "a+") as f:
                    f.write("TIME,%s\n" % logs[log])

    def log(self, filename, message):
        """ Write a timestamped message to a log

        Timestamps are floating points that indicate the amount of time since
        the current period was started.

        Args:
            filename: A string containing the name of the log to be written to.
            message: A string containing the message to be logged.
        """
        with open("%s/%s" % (self.output_directory, filename), "a") as f:
            f.write("%f,%s\n" % (time.time() - self.start_time, message))

    def rate_limit(self):
        """ Self-imposed rate limiting functionality

        THIS MUST BE RUN ONCE BEFORE EVERY REQUEST!!!!

        Limits the number of requests made by holding up the script if the
        number of requests made this period exceeds the number defined by the
        MAX_REQUESTS_PER_PERIOD global variable.
        """
        current_period_length = time.time() - self.request_period_start_time

        while ((current_period_length < PERIOD_LENGTH)
               and (self.traversed_this_period >= MAX_REQUESTS_PER_PERIOD)):
            print("Max requests per period reached (%d). %f Seconds until next "
                   "period." % (
                MAX_REQUESTS_PER_PERIOD, PERIOD_LENGTH - current_period_length))
            time.sleep(10)

            # End of period
            if ((time.time() - self.request_period_start_time) >= PERIOD_LENGTH):

                # Reset variables
                self.request_period_start_time = time.time()
                self.traversed_this_period = 0

                self.log("request_log.csv", self.traversed)

                # Create a new output directory
                self.initialize_output_directory()
            current_period_length = time.time() - self.request_period_start_time

        # Increment the counters
        self.traversed += 1
        self.traversed_this_period += 1

class DetailScraper(Scraper):
    """ Subclass of Scraper that specifically scrapes place details

    Attributes:
        dump_interval: An integer representing the number of place_ids traversed
            between each dump.
    """

    def __init__(self, api_key, output_directory_name, dump_interval = 50,
                 request_delay = 0.5, start_at = 0, writer = DEFAULT_WRITER):
        """ Initializes DetailScraper class

        Args:
            See Scraper.__init__.
            dump_interval: An integer representing the number of place_ids
                traversed between each dump.
            request_delay: An integer that overrides REQUEST_DELAY.
            start_at: The index of the place_ids array to start scraping at.
        """

        Scraper.__init__(self, api_key, output_directory_name, writer)
        self.dump_interval = dump_interval
        self.request_delay = request_delay
        self.start_at = start_at

    def scrape(self, target):
        """ The main function of DetailScraper

        Scrapes a list of place_ids using the Google Maps API's place details
        API.

        Args:
            target: One of the following:
                * A string containing the path to a JSON file which has been
                  created by process_output.py.
                * A string containing a single place_id
                * A list or tuple containing place_ids
        """

        place_ids = []
        results = []
        counter = 1

        if (type(target) is str):
            # File
            if (os.path.isfile(target)) and (target[-5:] == ".json"):
                ''' Old method of parsing the file used too much memory
                file_object = open(target)
                for datum in json.load(file_object):
                    place_ids.append(datum["place_id"])
                file_object.close()
                '''
                place_ids = subprocess.check_output(
                    ["grep", "-Po", "(?<=\"place_id\":).*?(?=\",)", target]
                ).replace(" ", "").replace("\"", "").rstrip("\n").split("\n")
                print("Added %d place_ids from %s" % (len(place_ids), target))

            # Single place_id
            else:
                place_ids.append(target)

        # Array of place_ids
        elif (type(target) is list) or (type(target) is tuple):
            if (type(target[0]) is str):
                place_ids += target

        if (len(place_ids) == 0):
            raise Exception("Invalid target supplied")

        if (self.start_at != 0):
            print("Skipping first %d place_ids" % self.start_at)
            place_ids = place_ids[self.start_at:]

        num_place_ids = len(place_ids)
        for place_id in place_ids:

            self.rate_limit() ##################################################

            # Dump results periodically
            if ((counter % self.dump_interval) == 0):
                print("Dumping last %d results" % self.dump_interval)
                self.writer.dump(results)
                results = []

            print("Scraping place_id %s (%d/%d - %0.3f%%)" % (
                place_id, counter, num_place_ids,
                float(counter)/num_place_ids*100,
            ))

            for attempt in range(MAX_RETRIES):
                try:
                    results.append(self.gmaps.place(place_id)["result"])
                    time.sleep(self.request_delay)
                    break
                except Exception as err:
                    print("Error: %s" % err)
                    self.log("error_log.csv", err)

                    time.sleep(self.request_delay)
                    pass
                print("Retrying (attempt #%d)" % (attempt + 1))

            if (attempt == MAX_RETRIES - 1):
                print("Max retries exceeded; skipping this place_id.")
                self.log(
                    "termination_log.csv",
                    ("Maximum number of retries exceeded. place_id: %s"
                     % place_id)
                )

            counter += 1

        # Dump remaining results
        self.writer.dump(results)

class SubdivisionScraper(Scraper):
    """ Subclass of Scraper specifically for building scrapers that use the
    subdivision scraping algorithm, defined below.

    A subclass of the Scraper class that contains functionality for scraping all
    of the places in a given area by scraping subdivisions of that area. This
    class alone does not have any functionality; it depends on self.scrape,
    which is left undefined by default.

    For actual scrapers, see the child classes PlacesTextScraper,
    PlacesNearbyScraper, and PlacesRadarScraper.

    Attributes:
        scrape = Undefined by default. scrape is a function to be defined by
            classes that inherit from SubdivisionScraper, which must take the
            following arguments, in order:
                latitude: The center latitude of the scrape area.
                longitude: The center longitude of the scrape area.
                radius_meters: The radius, in meters, of the scraping area.
                query: A string containing the place_type to be scraped in the
                    case of PlacesNearbyScraper and PlacesRadarScraper, or a
                    keyword in the case of PlacesTextScraper.
                subdivision_id_string: A string detailing the ancestry of the
                    current scrape area in the subdivision tree.
            scrape must return an array containing all of the results found in
            that scrape area.
        threshold = Undefined by default. A digit that describes the minimum
            number of results that the main scraping function needs to return,
            to trigger a recursion. The default is a little less than the
            maximum number of results that can be expected to be returned,
            defined by the Google Maps API documentation.
        gsm: a staticmaps.Constructor object used for generating Google Static
            Maps API links.
    """

    def scrape_subdivisions(self, min_latitude, max_latitude, min_longitude,
                            max_longitude, grid_width, query,
                            subdivision_parent_id = "root",
                            target_subdivision_id = ""):
        """ Recursive function that creates subdivisions and invokes the scraper

        This is the main function that manages the creation of subdivisions and
        invokes the scraper to scrape places from those subdivisions.

        Subdivisions are congruent rectangular areas which are similar to the
        region defined in the function's arguments. All subdivisions have the
        same width and height and are arranged in a square grid.

        For example, a 3x3 grid of subdivisions with min_lat = 0, min_long = 0,
        max_lat = 3, max_long = 3 would look like this:

            increasing latitude
            ^
            3 +---+---+---+
              | 7 | 8 | 9 |
            2 +---+---+---+
              | 4 | 5 | 6 |
            1 +---+---+---+
              | 1 | 2 | 3 |
            0 +---+---+---+
              0   1   2   3 > increasing longitude

        Where the number inside each box corresponds to the order in which that
        cell is processed.

        To calculate the scraping area, which is circular:
            We use the Pythagorean theorem to find the diameter of the smallest
                circle containing all points of the scraping area and divide
                that by 2 to get the radius.
            We get the average longitude and latitude to get the center.

        The scrape function is called on each cell and each cell is further
        subdivided into another square grid of congruent cells if the threshold,
        as defined in the initialization, is returned. To do this, the function
        recurses with the cell's region becoming the new grid's region.

        Each cell is assigned a string detailing that cell's ancestry. For
        example, the bottom left subdivision of the top right subdivision of the
        root cell has the ID "root -> 9 -> 1".

        To re-scrape a subdivision, all arguments except subdivision_parent_id
        must be supplied.

        Args:
            min_latitude, max_latitude, min_longitude, max_longitude: Floating
                points describing the bounds of the scraping region
            grid_width: An integer describing the number of rows and columns to
                subdivide the scraping region into. The total number of cells is
                grid_width^2.
            query: A string containing the place_type or keyword to be scraped
            subdivision_parent_id: A string containing the subdivision ID of the
                parent region. If there is no parent region, the ID is "root".
                This variable is managed by the function and should not be
                modified externally.
            target_subdivision_id: An optional string containing the subdivision
                ID of the cell to be skipped to. If defined, the function will
                only scrape subdivisions of that cell; all previous cells are
                ignored and the function terminates after all of that cell's
                subdivisions have been scraped.
        """

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
                                             + (subdivision_height
                                                * float(column)))
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
                subdivision_radius_meters = (math.sqrt((width_meters/2)**2
                                                  + (height_meters/2)**2))

                # This bool will be changed to true if more recursions are
                # necessary
                make_subdivisions = False

                if (len(split_id) == 0) or ("" in split_id):
                    print("Subdivision ID: %s" % subdivision_id_string)
                    print("Scrape name: %s" % self.output_directory_name)
                    print("Center coords: (%f, %f)" % (
                        subdivision_center_latitude,
                        subdivision_center_longitude
                    ))
                    print("Radius: %f meters" % subdivision_radius_meters)
                    print("Extents: ")
                    print({
                        "min_longitude": subdivision_min_longitude,
                        "max_longitude": subdivision_max_longitude,
                        "min_latitude": subdivision_min_latitude,
                        "max_latitude": subdivision_max_latitude
                    })
                    self.gsm.add_coords([
                        [subdivision_min_longitude, subdivision_min_latitude],
                        [subdivision_max_longitude, subdivision_min_latitude],
                        [subdivision_max_longitude, subdivision_max_latitude],
                        [subdivision_min_longitude, subdivision_max_latitude]
                    ], "polygon")
                    print("Visualization: %s" % self.gsm.generate_url())
                    self.gsm.reset()

                    # If the radius of the subdivision exceeds the max, skip the
                    # result collection and recurse
                    if (subdivision_radius_meters > MAX_RADIUS_METERS):
                        print("Making subdivisions because radius exceeded "
                              "maximum")
                        make_subdivisions = True

                    elif (subdivision_radius_meters < MIN_RADIUS_METERS):
                        print("Terminating branch because radius is below the "
                              "minimum")
                        self.log(
                            "termination_log.csv",
                            (("Radius fell below minimum value. Subdivision "
                              "ID: %s. Place type: %s. Coordinates: "
                              "(%f, %f) Radius: %f") % (
                                subdivision_id_string,
                                query,
                                subdivision_center_latitude,
                                subdivision_center_longitude,
                                subdivision_radius_meters)
                            )
                        )

                    else:

                        # Get results
                        results = self.scrape(subdivision_center_latitude,
                                              subdivision_center_longitude,
                                              subdivision_radius_meters,
                                              query,
                                              subdivision_id_string)
                        print("%d results for place_type %s" % (len(results),
                                                                query))
                        print("%d pages traversed since program was started"
                              % self.traversed)

                        # Save the results
                        self.writer.dump(results)

                        # If the number of results exceeded the threshold,
                        # recurse.
                        threshold = self.threshold

                        # HACK: Relax threshold for higher order subdivisions
                        depth = subdivision_id_string.count("->")
                        if (depth <= 4):
                            threshold = int(self.threshold * (1 - 0.6/depth))
                            print("Relaxing threshold to %d" % threshold)

                        if (len(results) >= threshold):
                            print("Making subdivisions because threshold was "
                                  "met (%d)" % threshold)
                            make_subdivisions = True

                else:
                    make_subdivisions = True

                # Recurse if necessary
                if (make_subdivisions):
                    print("")
                    self.scrape_subdivisions(subdivision_min_latitude,
                                             subdivision_max_latitude,
                                             subdivision_min_longitude,
                                             subdivision_max_longitude,
                                             3, query,
                                             subdivision_id_string,
                                             target_subdivision_id)
                else:
                    print("Branch terminated\n")

class PlacesNearbyScraper(SubdivisionScraper):
    """ A subclass of SubdivisionScraper specifically for scraping places_nearby

    A subclass that defines self.scrape as a function that fetches results from
    googlemaps.Client.places_nearby.

    Attributes:
        See SubdivisionScraper.
    """

    def __init__(self, *args, **kwargs):
        """ Initializes PlacesNearbyScraper class

        Args:
            See Scraper.__init__.
        """

        Scraper.__init__(self, *args, **kwargs)

        self.threshold = 50

        print("Configured scraper to scrape places_nearby; threshold = %d" % (
            self.threshold
        ))

    def scrape(self, latitude, longitude, radius_meters, query,
               subdivision_id_string, page = 1, retries = 0, token = "none"):
        """ Get points of interest from the Google Maps API using places_nearby

        Attempt to download all places in the given scrape area using the
        places_nearby function of the Google Maps API library. A maximum of
        MAX_RETRIES attempts are made before the function gives up and logs the
        branch termination to termination_log.csv.

        Because of how the API functions, scrape recurses if a next_page_token
        is returned in the results array.

        See the documentation of the "scrape" attribute in SubdivisionScraper
        for the main args.

        Args:
            page: An integer describing the number of pages traversed as of the
                current recursion.
            retries: An integer describing the number of attempts made as of the
                current recursion.
            token: A string containing a token that can be used to request the
                next page of results, passed by the previous recursion.

        Returns:
            An array containing places returned by the Google Maps API function.

            A blank array is returned if MAX_RETRIES attempts were made.
        """

        combined_results = []

        self.rate_limit() ######################################################

        print("Retrieving page %d" % page)
        try:
            # Only provide a page_token if the next_page_token was provided
            if (token == "none"):
                results = self.gmaps.places_nearby(
                    location = {
                        "lat": latitude,
                        "lng": longitude
                    },
                    radius = radius_meters,
                    type = query
                )
            else:
                results = self.gmaps.places_nearby(
                    location = {
                        "lat": latitude,
                        "lng": longitude
                    },
                    radius = radius_meters,
                    type = query,
                    page_token = token
                )

            # From https://developers.google.com/places/web-service/search:
            # "next_page_token contains a token that can be used to return up to
            # 20 additional results. A next_page_token will not be returned if
            # there are no additional results to display."
            # If the next_page_token exists, recurse and append to the
            # combined_results array.
            time.sleep(self.request_delay)
            if "next_page_token" in results:
                token = results["next_page_token"]
                combined_results += self.scrape(
                    latitude, longitude, radius_meters, query,
                    subdivision_id_string, page + 1, retries, token
                )

            combined_results += results["results"]

        except Exception as err:
            print("Error: %s" % err)
            self.log("error_log.csv", err)

            time.sleep(self.request_delay)

            if (retries <= MAX_RETRIES):
                print("Retrying (attempt #%d)" % (retries + 1))
                combined_results += self.scrape(
                    latitude, longitude, radius_meters, query,
                    subdivision_id_string, page, retries + 1, token
                )
            else:
                print("Max retries exceeded; skipping this subdivision.")
                self.log(
                    "termination_log.csv",
                    (("Maximum number of retries exceeded. Subdivision ID: %s. "
                      "Place type: %s. Coordinates: (%f, %f). Radius: %f") % (
                        subdivision_id_string,
                        query,
                        latitude,
                        longitude,
                        radius_meters
                    ))
                )

            pass

        return combined_results

class PlacesRadarScraper(SubdivisionScraper):
    """ A subclass of SubdivisionScraper specifically for scraping places_radar

    A subclass that defines self.scrape as a function that fetches results from
    googlemaps.Client.places_radar.

    Attributes:
        See SubdivisionScraper.
    """

    def __init__(self, *args, **kwargs):
        """ Initializes PlacesRadarScraper class

        Args:
            See Scraper.__init__.
        """

        Scraper.__init__(self, *args, **kwargs)

        self.threshold = 200

        print("Configured scraper to scrape places_radar; threshold = %d" % (
            self.threshold
        ))

    def scrape(self, latitude, longitude, radius_meters, query,
               subdivision_id_string):
        """ Get points of interest from the Google Maps API using the radar

        Attempt to download all places in the given scrape area using the
        places_radar function of the Google Maps API library. A maximum of
        MAX_RETRIES attempts are made before the function gives up and logs the
        branch termination to termination_log.csv.


        See the documentation of the "scrape" attribute in SubdivisionScraper
        for the main args.

        Returns:
            An array containing places returned by the Google Maps API function.

            A blank array is returned if MAX_RETRIES attempts were made.
        """

        results = []

        self.rate_limit() ######################################################

        for attempt in range(MAX_RETRIES):
            try:
                results = self.gmaps.places_radar(
                    location = {
                        "lat": latitude,
                        "lng": longitude
                    },
                    radius = radius_meters,
                    type = query
                )["results"]
                time.sleep(self.request_delay)
                break
            except Exception as err:
                print("Error: %s" % err)
                self.log("error_log.csv", err)

                time.sleep(self.request_delay)
                pass
            print("Retrying (attempt #%d)" % (attempt + 1))

        if (attempt == MAX_RETRIES - 1):
            print("Max retries exceeded; skipping this subdivision.")
            self.log(
                "termination_log.csv",
                (("Maximum number of retries exceeded. Subdivision ID: %s. "
                  "Place type: %s. Coordinates: (%f, %f). Radius: %f") % (
                    subdivision_id_string,
                    query,
                    latitude,
                    longitude,
                    radius_meters
                ))
            )

        return results

class PlacesTextScraper(SubdivisionScraper):
    """ A subclass of SubdivisionScraper specifically for scraping keyword
    searches

    A subclass that defines self.scrape as a function that fetches results from
    googlemaps.Client.places_radar, performing searches for a specific keyword.

    Attributes:
        See SubdivisionScraper.
    """

    def __init__(self, *args, **kwargs):
        """ Initializes PlacesTextScraper class

        Args:
            See Scraper.__init__.
        """

        Scraper.__init__(self, *args, **kwargs)

        self.threshold = 160

        print("Configured scraper to scrape places_radar using text search; "
              "threshold = %d" % (
            self.threshold
        ))

    def scrape(self, latitude, longitude, radius_meters, query,
               subdivision_id_string):
        """ Get points of interest from the Google Maps API using the radar

        Attempt to download all places in the given scrape area using the
        places_radar function of the Google Maps API library. A maximum of
        MAX_RETRIES attempts are made before the function gives up and logs the
        branch termination to termination_log.csv.

        Args:
            See the "scrape" attribute above.

        Returns:
            An array containing places returned by the Google Maps API function.

            A blank array is returned if MAX_RETRIES attempts were made.
        """

        results = []

        self.rate_limit() ######################################################

        for attempt in range(MAX_RETRIES):
            try:
                # Do an initial, exploratory radar search
                intermediate_results = self.gmaps.places_radar(
                    location = {
                        "lat": latitude,
                        "lng": longitude
                    },
                    radius = radius_meters,
                    keyword = query
                )["results"]
                time.sleep(self.request_delay)

                # Get the details of each radar search result
                current_place = 1
                for place in intermediate_results:
                    for place_attempt in range(MAX_RETRIES):

                        self.rate_limit() ######################################

                        try:
                            place_id = place["place_id"]
                            print("Fetching details for place %d of %d (%s)" % (
                                current_place, len(intermediate_results),
                                place_id
                            ))
                            results.append(self.gmaps.place(place_id)["result"])
                            current_place += 1
                            time.sleep(self.request_delay)
                            break
                        except Exception as err:
                            print("Error getting details: %s" % err)
                            self.log("error_log.csv", err)

                            time.sleep(self.request_delay)
                            pass

                    if (place_attempt == MAX_RETRIES - 1):
                        print("Max retries exceeded; skipping this place_id.")
                        self.log(
                            "termination_log.csv",
                            (("Maximum number of retries for a place exceeded. "
                              "place_id: %s. ") % place_id)
                        )

                break
            except Exception as err:
                print("Error: %s" % err)
                self.log("error_log.csv", err)

                time.sleep(self.request_delay)
                pass
            print("Retrying (attempt #%d)" % (attempt + 1))

        if (attempt == MAX_RETRIES - 1):
            print("Max retries exceeded; skipping this subdivision.")
            self.log(
                "termination_log.csv",
                (("Maximum number of retries exceeded. Subdivision ID: %s. "
                  "Place type: %s. Coordinates: (%f, %f). Radius: %f") % (
                    subdivision_id_string,
                    query,
                    latitude,
                    longitude,
                    radius_meters
                ))
            )

        return results