#!/usr/bin/env python3

import setuptools

setuptools.setup(
    name = "gmaps_scraper",
    version = "1.0.0",
    description = "Suite of tools for scraping place information using the "
                  "Google Maps API",
    packages = ["gmaps_scraper"],
    install_requires = ["googlemaps", "pyshp"]
)
