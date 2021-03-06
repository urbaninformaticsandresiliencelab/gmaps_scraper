#!/usr/bin/env python3

import setuptools

setuptools.setup(
    name = "gmaps_scraper",
    version = "1.2.2",
    description = "Suite of tools for scraping place information using the "
                  "Google Maps API",
    packages = ["gmaps_scraper"],
    install_requires = ["googlemaps", "pyshp"],
    entry_points = {"console_scripts": ["gmaps_scraper = gmaps_scraper.__main__:main"]}
)
