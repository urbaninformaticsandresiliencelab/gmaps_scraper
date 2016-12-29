import gmaps_subdivisions

details = gmaps_subdivisions.DetailScraper("2016-12-29_detail_of_2016-12-23_San_Francisco_California.json", 5)
details.scrape("output/json/2016-12-23_San_Francisco_California.json")
