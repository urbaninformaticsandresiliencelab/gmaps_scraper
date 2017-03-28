#!/usr/bin/env python

import glob
import os
import sys
import time

import parse_tiger
import scrapers

# There are 96 types of places that can be acquired
PLACE_TYPES = [
    "accounting",
    "airport",
    "amusement_park",
    "aquarium",
    "art_gallery",
    "atm",
    "bakery",
    "bank",
    "bar",
    "beauty_salon",
    "bicycle_store",
    "book_store",
    "bowling_alley",
    "bus_station",
    "cafe",
    "campground",
    "car_dealer",
    "car_rental",
    "car_repair",
    "car_wash",
    "casino",
    "cemetery",
    "church",
    "city_hall",
    "clothing_store",
    "convenience_store",
    "courthouse",
    "dentist",
    "department_store",
    "doctor",
    "electrician",
    "electronics_store",
    "embassy",
    "fire_station",
    "florist",
    "funeral_home",
    "furniture_store",
    "gas_station",
    "general_contractor",
    "gym",
    "hair_care",
    "hardware_store",
    "hindu_temple",
    "home_goods_store",
    "hospital",
    "insurance_agency",
    "jewelry_store",
    "laundry",
    "lawyer",
    "library",
    "liquor_store",
    "local_government_office",
    "locksmith",
    "lodging",
    "meal_delivery",
    "meal_takeaway",
    "mosque",
    "movie_rental",
    "movie_theater",
    "moving_company",
    "museum",
    "night_club",
    "painter",
    "park",
    "parking",
    "pet_store",
    "pharmacy",
    "physiotherapist",
    "plumber",
    "police",
    "post_office",
    "real_estate_agency",
    "restaurant",
    "roofing_contractor",
    "rv_park",
    "school",
    "shoe_store",
    "shopping_mall",
    "spa",
    "stadium",
    "storage",
    "store",
    "subway_station",
    "synagogue",
    "taxi_stand",
    "train_station",
    "transit_station",
    "travel_agency",
    "university",
    "veterinary_care",
    "zoo"
]


def scrape_subdivisions(options):
    """ Initialize and start a basic subdivision scraper

    Args:
        options: An array generated by an OptionParser
    """

    if (not os.path.isdir("tiger-2016/" + options.state)):
        print("Please specify a valid state with --state. See --help for more "
              "info. Possible states:")
        print(", ".join(sorted(os.listdir("tiger-2016/"))))
        sys.exit(1)
    state_shapefile = glob.glob("tiger-2016/" + options.state + "/*.shp")[0]

    city_extents = parse_tiger.get_extents(state_shapefile, options.city)
    if (not city_extents):
        print("Please specify a valid city with --city. See --help for more "
              "info. Possible states:")
        print(", ".join(sorted(parse_tiger.dump_names(state_shapefile))))
        sys.exit(1)

    if (not options.type in valid_scrape_types):
        print("Please specify a scrape type with --type. See --help for more "
                "info.")
        sys.exit(1)

    if (options.outdir):
        scraper_output_directory_name = options.outdir
    else:
        scraper_output_directory_name = ("%s_%s_%s_%s" % (
                                            time.strftime("%Y-%m-%d"),
                                            options.city, options.state,
                                            options.type
                                        )).replace(" ", "_")

    print
    if (options.type == "places_nearby"):
        new_scraper = scrapers.PlacesNearbyScraper(options.api_key,
                                          scraper_output_directory_name)
    elif (options.type == "places_radar"):
        new_scraper = scrapers.PlacesRadarScraper(options.api_key,
                                         scraper_output_directory_name)
    elif (options.type != "text_radar"):
        sys.exit(1)
    print

    if (options.type == "text_radar"):
        if (options.keyword is not None):
            scrapers.PlacesTextScraper(scraper_output_directory_name).scrape_subdivisions(
                city_extents["min_latitude"],
                city_extents["max_latitude"],
                city_extents["min_longitude"],
                city_extents["max_longitude"],
                3, options.keyword)
        else:
            print("Please specify a keyword with --keyword. See --help for "
                  "info.")
            sys.exit(1)
    else:
        types_to_scrape = PLACE_TYPES

        # Restrict the types to scrape if the user specifies
        if (options.categories is not None):
            types_to_scrape = options.categories.split(",")
            print("Restricting search to the following categories: %s"
                  % ", ".join(types_to_scrape))

        # For each place_type, in a places_nearby or places_radar scrape, the
        # subdivision -> extraction process is used.
        for place_type in types_to_scrape:
            new_scraper.scrape_subdivisions(city_extents["min_latitude"],
                                            city_extents["max_latitude"],
                                            city_extents["min_longitude"],
                                            city_extents["max_longitude"],
                                            3, place_type)

    print("Finished scraping %s, %s" % (options.city, options.state))

def scrape_errors(options):
    """ Initialize and start a subdivision error scraper

    Parse the warning_log.csv files of a scrape to find which ones were
    terminated because the maximum number of retries were exceeded, and
    re-scrape those subdivisions.

    Args:
        options: An array generated by an OptionParser
    """

    # An multidimensional array of all terminated branches to be re-scraped.
    # [n][0] = place_type
    # [n][1] = subdivision ID
    terminations = []

    scrapes = sorted(os.listdir(OUTPUT_DIRECTORY_ROOT))
    if (not options.rescrape in scrapes):
        print("Please enter a valid scrape name. Possible names:")
        print("\n".join(scrapes))
        sys.exit(1)

    # Parse termination logs
    for termination_log in glob.glob("%s/%s/*/termination_log.csv" % (
                                        OUTPUT_DIRECTORY_ROOT, options.rescrape
                                    )):
        file_object = open(termination_log)
        for line in file_object.readlines():
            if ("Maximum number of retries exceeded." in line):
                subdivision_id = line[line.find("root"):line.find(". Place")]
                place_type = line[(line.find("Place type: ")
                                   + len("Place type: "))
                                  :line.find(". Coordinates")]
                terminations.append([place_type, subdivision_id])
        file_object.close()

    # Parse scrape names to get the state and city. Some states have multiple
    # words, so iterate over all options and see which one matches state$ or
    # city$
    scrape_name_untimestamped = " ".join(options.rescrape.split("_")[1:-2])
    for state in os.listdir("tiger-2016/"):
        if ((scrape_name_untimestamped[-len(state):]) == state):

            state_shapefile = glob.glob("tiger-2016/" + state + "/*.shp")[0]

            for city in parse_tiger.dump_names(state_shapefile):
                city_name_end = len(scrape_name_untimestamped) - len(state) - 1
                if (city == (scrape_name_untimestamped[:city_name_end])):

                    print("Parsed location: %s, %s" % (city, state))
                    city_extents = parse_tiger.get_extents(state_shapefile,
                                                           city)
                    print

                    scraper_output_directory_name = ("%s_%s_%s" % (
                        time.strftime("%Y-%m-%d"),
                        options.rescrape,
                        "errors"
                    )).replace(" ", "_")
                    scraper_type = "_".join(options.rescrape.split("_")[-2:])
                    if (scraper_type == "places_nearby"):
                        new_scraper = scrapers.PlacesNearbyScraper(
                            options.api_key, scraper_output_directory_name
                        )
                    elif (scraper_type == "places_radar"):
                        new_scraper = scrapers.PlacesRadarScraper(
                            options.api_key, scraper_output_directory_name
                        )
                    else:
                        print("Error: could not re-scrape scrape_type %s "
                              % scraper_type)
                        return

                    for termination in terminations:
                        print("Scraping place_type %s of subdivision %s" % (
                            termination[0], termination[1]
                        ))
                        new_scraper.scrape_subdivisions(
                            city_extents["min_latitude"],
                            city_extents["max_latitude"],
                            city_extents["min_longitude"],
                            city_extents["max_longitude"],
                            3,
                            termination[0],
                            target_subdivision_id = termination[1]
                        )

def scrape_details(options):
    """ Initialize and start a detail scraper

    Thin wrapper that initalizes a DetailScraper, given the name of a formatted
    JSON generated by process_pickles.py or create_json_parallel_redis.py

    Args:
        options: An array generated by an OptionParser
    """

    jsons = sorted(os.listdir(JSON_DIRECTORY))
    if (not options.details in jsons):
        print("Please enter a valid JSON name. Possible names:")
        print("\n".join(jsons))
        sys.exit(1)

    details = DetailScraper(options.api_key, "%s_%s_details" % (
        time.strftime("%Y-%m-%d"),
        options.details
    )).scrape("%s/%s" % (JSON_DIRECTORY, options.details))


if (__name__ == "__main__"):
    valid_scrape_types = ["places_radar", "places_nearby", "text_radar"]
    api_key = None

    try:
        import credentials
        if (credentials.api_key != "Enter key here"):
            api_key = credentials.api_key
    except:
        pass

    import optparse
    parser = optparse.OptionParser()
    parser.add_option("--api-key", dest = "api_key", metavar = "API_KEY",
                      help = "API key to initialize the scraper with",
                      default = api_key)
    parser.add_option("--scrape-errors", dest = "rescrape",
                      metavar = "SCRAPE_NAME",
                      help = "Re-scrape terminated branches from the given "
                             "scrape. Overrides all other options.")
    parser.add_option("--scrape-details", dest = "details",
                      metavar = "JSON_NAME",
                      help = "Scrape details from the given formatted JSON. "
                             "Overrides all other options except "
                             "--scrape-errors.")
    parser.add_option("--state", dest = "state", metavar = "STATE",
                      help = "Use the shapefile located in tiger-2016/STATE",
                      default = "null")
    parser.add_option("--city", dest = "city", metavar = "CITY",
                      help = "Scrape the CITY shape in the chosen shapefile")
    parser.add_option("--type", dest = "type", metavar = "TYPE",
                      help = "Use a scraper of the specified TYPE. Types: %s"
                              % ", ".join(valid_scrape_types))
    parser.add_option("--keyword", dest = "keyword", metavar = "KEYWORD",
                      help = "For text_radar scrapers: perform a text search "
                             "for KEYWORD")
    parser.add_option("--categories", dest = "categories",
                      metavar = "CATEGORIES",
                      help = "A list of types to restrict the places_nearby or "
                             "places_radar search to, separated by commas")
    parser.add_option("--outdir", dest = "outdir", metavar = "OUTDIR",
                      help = "(Optional) Write all results to subdirectories "
                             "of OUTDIR")
    (options, args) = parser.parse_args()

    if (options.api_key is None):
        if (not os.path.isfile("credentials.py")):
            print("Could not find credentials.py. One has been created for "
                  "you.")
        credentials_file = open("credentials.py", "w")
        credentials_file.write("# Google maps API key to be used by the "
                               "scraper\n"
                               "api_key = \"Enter key here\"\n")
        credentials_file.close()
        print("Please provide an API key by adding it to credentials.py or "
              "by using the --api-key option.")
        raise ValueError("No valid API key string given")
    else:
        if (options.rescrape is not None):
            scrape_errors(options)
        elif (options.details is not None):
            scrape_details(options)
        else:
            scrape_subdivisions(options)
