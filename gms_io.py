#!/usr/bin/env python
# Library providing data dumping classes in a modular way for gmaps_scraper

import cPickle

try:
    import pymongo
    class MongoWriter(object):
        """ Handles writing to a MongoDB collection

        Args:
            collection: A pymongo.collection.Collection object to be written to.
        """

        def __init__(self, db_name, collection_name, host = "localhost:27017"):
            """ Initializes the MongoWriter class

            Args:
                db_name: A string containing the name of the database.
                collection_name: A string containing the name of the collection.
                host: A string containing the name of the host and its port.
            """

            self.collection = pymongo.MongoClient(host)[db_name][collection_name]

        def dump(self, data, dump_many = False):
            """ Write data to the previously defined collection

            Args:
                data: A dictionary object or iterable to be written to the
                    collection.
                dump_many: A boolean indicating whether or not data consists of one
                    dictionary or many dictionaries.
            """

            if (dump_many):
                self.collection.insert_many(data)
            else:
                self.collection.insert_one(data)
except:
    print("MongoWriter class unavailable; pymongo not found")

class PickleWriter(object):
    """ Handles writing to a pickle file

    Attributes:
        pickle_path: A string containing a path to a pickle file.
    """

    def __init__(self, pickle_path):
        """ Initializes PickleWriter class

        Args:
            pickle_path: A string containing a path to a pickle file.
        """

        self.pickle_path = pickle_path

    def dump(self, data):
        """ Dump data to a pickle object

        Args:
            data: A Python data structure to be dumped to the pickle file.
        """

        with open(self.pickle_path, "a+b") as f:
            cPickle.dump(data, f)
