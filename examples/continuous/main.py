#!/usr/bin/env python3
# continuous scraping of the top 50 U.S. cities, dumping to mongo.places_db
# collections are labeled yyyy-mm-dd-city_name

import collections
import csv
import datetime
import pymongo

import gmaps_scraper

API_KEY = "API_KEY_HERE"

with open("top50cities.csv", "r") as f:
    BOUNDING_BOXES = collections.OrderedDict(
        (
            row["city"],
            {
                key: float(row[key])
                for key in sorted(list(row.keys()))[1:]
            }
        )
        for row in csv.DictReader(f)
    )

def scrape_city(city):
    """ Scrape a city

    Args:
        city: The value in the "city" column in top50cities.csv
    """

    scrape_name = "%s_%s" % (
        datetime.datetime.now().strftime("%Y-%m-%d"),
        city.replace(" ", "_")
    )

    gmaps_scraper.scrapers.PlacesNearbyScraper(
        api_key = API_KEY,
        output_directory_name = scrape_name,
        writer = "mongo"
    ).scrape_subdivisions(
        grid_width = 3,
        query = "", # no place_type causes google to return all place types
        **BOUNDING_BOXES[city]
    )

if (__name__ == "__main__"):
    while True:
        for city in BOUNDING_BOXES:
            scrape_city(city)
