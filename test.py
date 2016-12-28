import glob
import json
import sys

import geo
import parse_tiger

js = open("output/json/2016-12-27_Boston_Massachusetts_places_radar.json")
data = json.load(js)
js.close()

polygon = parse_tiger.dump_points(glob.glob("tiger-2016/Massachusetts/*.shp")[0], "Boston")

data_in_polygon = []
progress = 0
progress_goal = len(data)
for datum in data:
    point = (datum["geometry"]["location"]["lng"],
             datum["geometry"]["location"]["lat"])
    if (geo.point_in_polygon(point, polygon)):
        data_in_polygon.append(datum)
    progress += 1
    sys.stdout.write("Progress: %0.3f%%\r" % (float(progress)/progress_goal*100))
    sys.stdout.flush()
print

out = open("datum_in_polygon_radar.json", "w")
json.dump(data_in_polygon, out, indent = 4, separators=(',', ': '))
out.close()
