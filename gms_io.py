#!/usr/bin/env python
# Library providing data dumping classes in a modular way for gmaps_scraper

# TODO: update documentation

import cPickle
import json
import os

class DummyDuplicateChecker(object):
    """ A dummy class to be used when RedisDuplicateChecker is not available

    This class provides dummy functions to mimic RedisDuplicateChecker's
    functionality, but does not actually check for duplicates or perform any
    other functions.
    """

    def check(self, *args):
        return True
    def flush(self):
        pass

try:
    import redis
    class RedisDuplicateChecker(object):
        def __init__(self, set_name = "seen_places", redis_db = 0,
                     redis_host = "localhost", redis_port = 6379):
            # Test to make sure Redis is running
            r = redis.StrictRedis()
            self.redis = redis.StrictRedis(host = redis_host,
                                           port = redis_port, db = redis_db)
            self.redis.set("RedisDuplicateCheckerTest", 1)
            self.redis.delete("RedisDuplicateCheckerTest")
            self.set_name = set_name

        def check(self, place_id):
            """ Checks to see if place_id has already been dumped

            Args:
                place_id: A string containing the place_id to be checked.

            Returns:
                True if the place_id does not exist yet; False if it does.
            """
            return self.redis.sadd(self.set_name, place_id) == 1

        def flush(self):
            """ Empties the working set """
            self.redis.delete(self.set_name)
except:
    print("RedisDuplicateChecker class unavailable; could not import "
                  " redis.")

class Writer(object):
    """ Base Writer class

    Attributes:
        duplicate_checker: Either a RedisDuplicateChecker or
            DummyDuplicateChecker object, depending on the availability of
            Redis.
    """

    def __init__(self, *redis_args):
        """ Initializes self.duplicate_checker and defines self.flush

        Args:
            redis_args: A dictionary of keyword arguments. See
                RedisDuplicateChecker.__init__ for more information.
        """

        self.duplicate_checker = DummyDuplicateChecker()
        try:
            self.duplicate_checker = RedisDuplicateChecker(*redis_args)
        except Exception as err:
            print("Could not initialize RedisDuplicateChecker: %s" % err)
            print("Using DummyDuplicateChecker instead")

try:
    import pymongo
    class MongoWriter(Writer):
        """ Handles writing to a MongoDB collection

        Attributes:
            collection: A pymongo.collection.Collection object to be written
                to.
            duplicate_checker: Either a RedisDuplicateChecker or
                DummyDuplicateChecker object, depending on the availability of
                Redis.
        """

        def __init__(self, collection_name, db_name = "places_db",
                     host = "localhost:27017", *redis_args):
            """ Initializes the MongoWriter class

            Args:
                db_name: A string containing the name of the MongoDB
                    database.
                collection_name: A string containing the name of the
                    MongoDB collection.
                    that stores seen place_ids.
                host: A string containing the name of the MongoDB host
                    and its port.
                redis_args: A dictionary of keyword arguments. See
                    RedisDuplicateChecker.__init__ for more information.
            """

            Writer.__init__(self, *redis_args)
            self.collection = pymongo.MongoClient(host)[db_name][collection_name]

        def dump(self, data):
            """ Write data to the previously defined collection, checking for
            duplicates first

            Args:
                data: An iterable containing dictionaries to be written to the
                    collection.
            """
            for _dict in data:
                if (self.duplicate_checker.check(_dict["place_id"])):
                    self.collection.insert_one(_dict)
except:
    print("MongoWriter class unavailable; could not import pymongo")

class PickleWriter(Writer):
    """ Handles writing to a pickle file

    Attributes:
        pickle_path: A string containing a path to a pickle file.
    """

    def __init__(self, pickle_path):
        """ Initializes PickleWriter class """
        self.pickle_path = pickle_path

    def dump(self, data):
        """ Dump data to a pickle object

        Args:
            data: A Python data structure to be dumped to the pickle file.
        """

        with open(self.pickle_path, "a+b") as f:
            cPickle.dump(data, f)

class JSONWriter(Writer):
    """ Handles writing to a JSON

    Attributes:
        json_path: A string containing a path to a JSON file.
        duplicate_checker: Either a RedisDuplicateChecker or
            DummyDuplicateChecker object, depending on the availability of
            Redis.
    """

    def __init__(self, json_path, *redis_args):
        """ Initializes JSONWriter class and output file

        Args:
            json_path: A string containing a path to a JSON file.
            redis_args: A dictionary of keyword arguments. See
                RedisDuplicateChecker.__init__ for more information.
        """

        Writer.__init__(self, *redis_args)
        self.json_path = json_path

        if (not os.path.isfile(json_path)):
            with open(json_path, "w") as f:
                f.write("[\n\n]")

    def dump(self, data):
        """ Dump data to a JSON file, checking for duplicates first

        Args:
            data: An iterable containing dictionaries to be dumped.
        """

        with open(self.json_path, "r+") as f:
            if (len(data) > 0):
                f.seek(-2, os.SEEK_END)
                for _dict in data:
                    if (self.duplicate_checker.check(_dict["place_id"])):
                        json.dump(_dict, f)
                        f.write(",\n")
                    else:
                        print("Ignoring duplicate %s" % _dict["place_id"])
                f.seek(-2, os.SEEK_END)
                f.write("\n]")
