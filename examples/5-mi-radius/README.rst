scrape a 5 mile perimeter around a city
=======================================

small script that uses ``gmaps-scraper`` to scrape a 7 mile thick perimeter
around the top 50 most populous cities in the united states in order from most
populous to least populous until stopped, dumping data to the ``places_db``
database in MongoDB.

``top50cities.csv`` was generated using TIGER 2016 shapefiles; city names are
taken from the same shapefiles
