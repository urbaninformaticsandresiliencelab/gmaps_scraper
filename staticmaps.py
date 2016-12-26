#!/usr/bin/env python
# Small library for generating URLs of visualizations

class Constructor(object):
    def __init__(self):
        self.parameters = []

    def generate_url(self, size = "400x400"):
        return "&".join(["https://maps.googleapis.com/maps/api/staticmap?size=%s" % size] + self.parameters)

    def add_coords(self, new_points, _type = "markers", color = "0x00ff0066"):
        if (_type == "markers"):
            new_parameters = "markers=color:%s|size:tiny" % color
        elif (_type == "path"):
            new_parameters = "path=color:%s|weight:5" % color
        elif (_type == "polygon"):
            new_parameters = "path=color:0x00000000|fillcolor:%s|weight:5" % color

        for point in new_points:
            new_parameters += "|%f,%f" % (point[1], point[0])

        self.parameters.append(new_parameters)

    def reset(self):
        self.parameters = []
