import gmaps_subdivisions
import glob

#details = gmaps_subdivisions.DetailScraper("2016-12-29_detail_of_2016-12-23_San_Francisco_California.json", 5)
#details.scrape("output/json/2016-12-23_San_Francisco_California.json")

scrape_name = glob.glob("output/raw_pickle/*")[0]
#scraper = gmaps_subdivisions.PlaceScraper(scrape_name, "places_nearby")
for termination_log in glob.glob("%s/*/termination_log.csv" % scrape_name):
    file_object = open(termination_log)
    for line in file_object.readlines():
        if ("Maximum number of retries exceeded." in line):
            subdivision_id = line[line.find("root"):line.find(". Place")]
            place_type = line[(line.find("Place type: ") + len("Place type: "))
                              :line.find(". Coordinates")]
            print(place_type, subdivision_id)
    file_object.close()
