#/usr/bin/env python

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

import glob
import os

import parse_tiger

class Gui(Gtk.Window):

    def __init__(self):
        Gtk.Window.__init__(self, title = "gmaps-scraper GUI")

        self.grid = Gtk.Grid()
        self.add(self.grid)

        self.state_menu = Gtk.ComboBoxText()
        self.state_menu.append_text("Choose a State")
        self.state_menu.set_active(0)
        states = os.listdir("tiger-2016")
        states.sort()
        map(self.state_menu.append_text, states)

        self.city_menu = Gtk.ComboBoxText()

        self.scrape_menu = Gtk.ComboBoxText()

        self.start_button = Gtk.Button.new_with_label("Start Scraping")
        self.start_button.set_sensitive(False)

        self.city_menu.connect("changed", self.city_menu_changed)
        self.state_menu.connect("changed", self.state_menu_changed)
        self.scrape_menu.connect("changed", self.scrape_menu_changed)
        self.start_button.connect("clicked", self.start_button_clicked)

        self.grid.attach(self.state_menu, 0, 0, 4, 1)
        self.grid.attach(self.city_menu, 0, 1, 4, 1)
        self.grid.attach(self.scrape_menu, 0, 2, 4, 1)
        self.grid.attach(self.start_button, 1, 3, 2, 1)

    def state_menu_changed(self, widget):
        text = self.state_menu.get_active_text()

        self.city_menu.remove_all()
        self.scrape_menu.remove_all()
        self.start_button.set_sensitive(False)

        if (text != "Choose a State"):

            self.city_menu.append_text("Choose a City")
            self.city_menu.set_active(0)
            cities = parse_tiger.dump_names(glob.glob("tiger-2016/%s/*.shp" % text)[0])
            cities.sort()
            map(self.city_menu.append_text, cities)

    def city_menu_changed(self, widget):
        text = self.city_menu.get_active_text()

        self.scrape_menu.remove_all()
        self.start_button.set_sensitive(False)

        if (text != "Choose a City"):
            for item in ["Choose a Scrape Mode", "scrape_nearby", "scrape_radio"]:
                self.scrape_menu.append_text(item)
            self.scrape_menu.set_active(0)

    def scrape_menu_changed(self, widget):
        text = self.scrape_menu.get_active_text()

        if (text != "Choose a Scrape Mode"):
            self.start_button.set_sensitive(True)
        else:
            self.start_button.set_sensitive(False)

    def start_button_clicked(self, widget):
        Gtk.main_quit()

win = Gui()
win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main()
