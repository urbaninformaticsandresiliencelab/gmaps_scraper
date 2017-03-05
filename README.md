gmaps-scraper
=============

*gmaps-scraper* is a suite of tools designed to facilitate the scraping and
processing of place data using the Google Maps API.

Table of Contents
=================
Code Overview
-------------
For scraping:

* gmaps\_subdivisions.py - The main scraping script.

For processing:

* process\_pickles.py - A script to automate the archiving of pickles and the
  creation of merged and deduplicated JSONs.
* create\_json\_parallel\_redis.py - A script to process a single pickle
  collection very fast by using Redis as a shared memory store for multiple
  worker processes.

Additional libraries used by the scraper:

* geo.py - A library providing various geometric functions such as the haversine
    formula, the law of cosines, and a function for point-in-polygon.
* gms\_io.py - A library providing various classes that handle the writing of
    scraped data to various formats.
* parse\_tiger.py - A library providing wrapper functions for parsing the US
    Census TIGER data by using the shapefile library.
* staticmaps.py - A library that generates valid Google Static Maps API URLs for
    visualizing areas on Google Maps.

Utility scripts:

* scrape\_tiger.sh - Scrape and process US Census TIGER data for use by the
    various scripts.

Setup
-----
Usage
-----
* Scraping
* Processing
* Using grep to Count Occurances of Patterns

Code Overview
=============
Scripts are documented internally and formatted in accordance with [Google's
Python styleguide](https://google.github.io/styleguide/pyguide.html). For more
in-depth documentation, refer to the comments and docstrings located in each
script.

gmaps\_subdivisions.py
----------------------
*gmaps_scraper.py* scrapes places from Google Maps by subdividing a chosen
area into smaller areas and making a requests for places in that area, making
further subdivisions if a certain threshold is met, by default the maximum
number of results defined by the
[Google Places API Web Service documentation](https://developers.google.com/places/web-service/search)
with a little bit of head space (50 instead of 60, as of the time of writing
this). Additionally, a bug was discovered where places\_nearby searches over a
large area with more than 60 results would return less than 60 results, so the
threshold is automatically relaxed for the first few subdivisions in the
hierarchy using the formula

    ADJUSTED_THRESHOLD = ACTUAL_THRESHOLD * (1 - 0.6 / HIERARCHY_DEPTH)

More information about the scraping algorithm is documented in the
*scrape_subdivisions* method of the *SubdivisionScraper* class. From the script:

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

    The scraper function is called on each cell and each cell is further
    subdivided into another square grid of congruent cells if the threshold,
    as defined in the initialization, is met. To do this, the function recurses
    with the cell's region becoming the new grid's region.

    Each cell is assigned a string detailing that cell's ancestry. For
    example, the bottom left subdivision of the top right subdivision of the
    root cell has the ID "root -> 9 -> 1".

Because each cell in the entire scraping tree is assigned a unique ID, we can
later re-scrape cells that have been abandoned due to exceeding the maximum
number of retries, as defined by the *MAX_RETRIES* constant, or cells that
exhibit strange behaviour:

    To re-scrape a subdivision, all arguments except subdivision_parent_id
    must be supplied.

*gmaps_scraper.py* provides the following classes:

* Scraper: A class for building generic Google Maps API scrapers
    * DetailScraper: A child class of Scraper built for scraping place details
    * SubdivisionScraper: A child class of Scraper meant for building scrapers
      that use the subdivisions algorithm, defined above.
        * PlacesNearbyScraper: A child class of SubdivisionScraper built for
          scraping the places_nearby API call.
        * PlacesRadarScraper: A child class of SubdivisionScraper built for
          scraping the places_radar API call. This currently has buggy behaviour
          and PlacesNearbyScraper should be used instead.
        * PlacesTextScraper: A child class of SubdivisionScraper built for
          scraping the places_radar API call, filtering results by using a
          given keyword.

The writing of scraped data is handled by *gms_io.py*, which has the ability to
deduplicate on the fly. More information can be found under the *gms_io.py*
section.

process\_pickles.py
-------------------
Due to the nature of the scraper, the output pickle files, which are appended to
after every successful request, contain a massive amount of duplicates. The
*process\_pickles.py* script is responsible for automating the deduplication of
scrape data. The script:

* Obtains a list of all scrapes in *gmaps\_subdivisions.py*'s output directory
    by using the glob library.
* For each scrape, merge and deduplicate the pickled data if a JSON does not
    exist yet.
* For each scrape, compress the pickled data into a .tar.xz file if one does not
    exist yet.

The script utilizes Python's multiprocessing library to make fuller use of
system resources by doing multiple merges and compressions at the same time. The
number of worker processes is defined by the *THREADS* constant, which is, by
default, 3.

create\_json\_parallel\_redis.py
--------------------------------
*create\_json\_parallel\_redis.py* takes advantage of Redis' ability to serve as
a very fast and light cache to speed up the merging and deduplication of a
single scrape by starting multiple worker processes on different pickles of the
same scrape, using Redis as shared dictionary of already-seen place IDs. For
deduplication, scripts make use of Redis' [Get](https://redis.io/commands/get)
and [Set](https://redis.io/commands/set) functions, which are both atomic and of
O(1) complexity. As was the case in process\_pickles.py, the number of worker
processes is defined by the *THREADS* constant, which is, by default, 4.

geo.py
------
*geo.py* is a small library providing primitive geometric functions that are
used in *gmaps\_subdivisions.py*. Functions included:

* point\_in\_polygon - A function that returns True if a point is in a polygon
    and False if otherwise.
* haversine and law\_of\_cosines - Calculate the distance between two points on
    a sphere.

gms\_io.py
----------
*gms_io.py* handles the saving of scraped data to various file formats or
databases and provides two families of classes: duplicate checkers and writers.

Duplicate checkers have two methods: *check*, which checks to see if a place has
already been saved, and *flush*, which clears the list of seen places. These are
used by writer classes, which have a single dump method that takes an array of
dictionaries as input and saves the given dictionaries to an output destination.

Duplicate checker classes provided:
* DuplicateChecker: The base class to use when no other classes can be
  instanced or duplicate checking is not desired. This mimics the behaviour
    of other duplicate checkers but does not actually do any checking.
    * SQLite3DuplicateChecker: A duplicate checker that checks against an SQLite
      database.
    * RedisDuplicateChecker: A duplicate checker that checks against a Redis
      set.

Writer classes provided:
* Writer: Base writer class that provides no functionality other than the
  initialization of a duplicate checker.
    * MongoWriter: Handles writing to a MongoDB collection.
    * PickleWriter: Handles writing to a pickle files, separated by period. This
      was previously the default "writer" of *gmaps_scraper.py*.
    * JSONWriter: Handles writing to a JSON file.

parse\_tiger.py
---------------
*parse_tiger.py* provides simple wrapper operations tailored for processing US
Census TIGER shapefiles. Functions included:

* dump\_names - Return an array of all places included in a shapefile.
* dump\_points - Return an array of all points included in a shapefile. This can
    be narrowed down to a single city.
* get\_extents - Return the most extreme coordinates of a shapefile. This can be
    narrowed down to a single city.

staticmaps.py
-------------
*staticmaps.py* provides a Constructor class which is used to generate valid
Google Static Maps API URLs. Class methods:

* generate\_url - Combine stored shapes into a single URL.
* add\_coords - Add coordinates to the current static map in the form of
    individual markers, a path, or a polygon..
* reset - Remove all stored shapes.

scrape\_tiger.sh
----------------
*scrape\_tiger.sh* is a script that is run once in the setup to scrape and
process US Census TIGER data. The script downloads data, decompresses it, and
organizes it according to the name of the state that each archive contains.

Setup
=====
Before doing anything, you must first cd into this directory. Once that is done,
run *scrape-tiger.sh*, which will scrape the TIGER data, placing it into a
directory named *tiger-2016-src/*:

    ./scrape-tiger.sh

It will then process this data, placing the organized data in a directory named
*tiger-2016/*. At this point, *tiger-2016-src/* can be removed if you wish.

The next step is to create a *credentials.py* if you do not already have one. To
create a new one, run *gmaps_scraper.py* once; it should create a template
for you:

    ./gmaps_scraper.py

Enter the appropriate keys and save the file.

Usage
=====
As in the setup, you must cd into this directory before running any of the
scripts.

Scraping
--------
To scrape a city, supply the necessary arguments to *gmaps_scraper.py*.
More information on what arguments to supply can be viewed by passing the
*--help* argument:

    ./gmaps_scraper.py --help

For example, to scrape Boston, Massachusetts using the places\_nearby scraper:

    ./gmaps_scraper.py --type places_nearby --city Boston --state Massachusetts

Processing
----------
As stated in the Code Overview section, there are two scripts that can merge and
deduplicate the pickled scrape data, outputting JSON files. The simplest thing
to do is to run the *process_pickles.py* script, which will automate all
merging, deduplicating, and archiving:

    ./process_pickles.py

For particularly large scrapes, such as those of New York City or Los Angeles,
you may prefer to use *create_json_parallel_redis.py*. To use this script, you
must [download and build Redis](https://redis.io/download) or install it using
your distribution's package manager. After you have *redis-server* up and
running, you can run the script, which will prompt you to choose a single
scrape directory to work with:

    ./create_json_parallel_redis.py

After the script finishes, you may want to remove the *dump.rdb* file created in
whatever directory you ran *redis-server* from. The database is cleared before
each merge and deduplication, so there is no merit to keeping this file.

Using grep to Count Occurances of Patterns
------------------------------------------
A very fast and convenient way to count how many times a pattern appears, such
as "atm" if you want to find the number of ATMs in a scrape or "place\_id" if
you want to find the number of unique places in a scrape, is to use GNU grep
from the GNU coreutils. To quickly count the number of times something occurs,
use the following syntax:

    grep PATTERN FILE | wc -l

Where *PATTERN* is a regular expression that you want to find and *FILE* is the
file to be searched. For example, to find the number of ATMs in Boston:

    grep atm output/json/2016-12-26_Boston_Massachusetts_places_nearby.json | wc -l

grep is particularly fast at searching plaintext files, such as the JSONs
created by *gmaps-scraper*:

    $ file=output/json/2016-12-27_New_York_New_York_places_nearby.json 
    $ du $file
    359M    output/json/2016-12-27_New_York_New_York_places_nearby.json
    $ time grep atm $file | wc -l
    10082

    real    0m5.934s
    user    0m0.415s
    sys 0m0.357s
