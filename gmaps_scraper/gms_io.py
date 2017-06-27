#!/usr/bin/env python3
# Library providing data dumping classes in a modular way for gmaps_scraper

import pickle
import json
import os
import sqlite3

class DuplicateChecker(object):
    """ A dummy class to be used when deduplication is not desirable

    This class provides dummy functions to mimic duplicate checking
    functionality, but does not actually check for duplicates or perform any
    other functions.
    """

    def __init__(self, *args, **kwargs):
        pass

    def check(self, *args, **kwargs):
        return True

    def flush(self):
        pass

class SQLite3DuplicateChecker(DuplicateChecker):
    def __init__(self, table = "seen_places", db_path = "seen_places.db"):
        self.table = table
        self.db_path = db_path
        with sqlite3.connect(self.db_path) as connection:
            try:
                connection.execute("CREATE TABLE %s (id)" % self.table)
                connection.commit()
            except:
                pass

    def check(self, place_id):
        with sqlite3.connect(self.db_path) as connection:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO %s VALUES (?)" % self.table,
                           (place_id,))
            cursor.execute("SELECT Count(id) FROM %s WHERE id=?" % self.table,
                           (place_id,))
            connection.commit()
            return cursor.fetchone()[0] == 1

    def flush(self):
        with sqlite3.connect(self.db_path) as connection:
            try:
                connection.execute("DELETE FROM %s" % self.table)
                connection.commit()
            except:
                pass

try:
    import redis
    class RedisDuplicateChecker(DuplicateChecker):
        def __init__(self, set_name = "seen_places", redis_db = 0,
                     redis_host = "localhost", redis_port = 6379):
            # Test to make sure Redis is running
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
          " redis module.")

class Writer(object):
    """ Base Writer class

    Attributes:
        duplicate_checker: An object of the DuplicateChecker class or of one of
            its child classes.
    """

    def __init__(self, *args, **kwargs):
        """ Initializes self.duplicate_checker as a DuplicateChecker by default
        """

        self.duplicate_checker = DuplicateChecker(*args, **kwargs)

try:
    import pymongo
    class MongoWriter(Writer):
        """ Handles writing to a MongoDB collection

        Attributes:
            collection: A pymongo.collection.Collection object to be written
                to.
            duplicate_checker: An object of the DuplicateChecker class or of one
                of its child classes.
        """

        def __init__(self, collection_name, db_name = "places_db",
                     host = "localhost:27017", *args, **kwargs):
            """ Initializes the MongoWriter class

            Note: MongoDB handles deduplication internally, so the
            deduplicators are ignored by MongoWriter.

            Args:
                db_name: A string containing the name of the MongoDB
                    database.
                collection_name: A string containing the name of the
                    MongoDB collection.
                    that stores seen place_ids.
                host: A string containing the name of the MongoDB host
                    and its port.
                args: A dictionary of keyword arguments. See
                    RedisDuplicateChecker.__init__ for more information.
            """

            Writer.__init__(self, *args, **kwargs)
            self.collection = pymongo.MongoClient(host)[db_name][collection_name]
            if (not "place_id_1" in self.collection.index_information().keys()):
                self.collection.create_index(
                    [("place_id", pymongo.ASCENDING)],
                    unique = True
                )

        def dump(self, data):
            """ Write data to the previously defined collection, checking for
            duplicates first

            Args:
                data: An iterable containing dictionaries to be written to the
                    collection.
            """
            for _dict in data:
                # Using duplicate checkers is deprecated for MongoWriter
                #if (self.duplicate_checker.check(_dict["place_id"])):
                #    self.collection.insert_one(_dict)

                try:
                    self.collection.insert_one(_dict)
                except pymongo.errors.DuplicateKeyError:
                    print("Ignoring duplicate %s" % _dict["place_id"])
except:
    print("MongoWriter class unavailable; could not import pymongo")

try:
    import psycopg2
    class PostgresWriter(Writer):
        """ Handles writing to a MongoDB collection

        """

        def __init__(self):
            # TODO
            pass

        def dump(self, data):
            # TODO
            for _dict in data:
                pass
except:
    print("PostgresWriter class unavailable; could not import psycopg2")

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
            for _dict in data:
                if (self.duplicate_checker.check(_dict["place_id"])):
                    pickle.dump(data, f)
                else:
                    print("Ignoring duplicate %s" % _dict["place_id"])

class JSONWriter(Writer):
    """ Handles writing to a JSON

    Attributes:
        json_path: A string containing a path to a JSON file.
        duplicate_checker: An object of the DuplicateChecker class or of one of
            its child classes.
    """

    def __init__(self, json_path, *args, **kwargs):
        """ Initializes JSONWriter class and output file

        Args:
            json_path: A string containing a path to a JSON file.
            args: A dictionary of keyword arguments. See
                RedisDuplicateChecker.__init__ for more information.
        """

        Writer.__init__(self, *args, **kwargs)
        self.json_path = json_path

        if (not os.path.isfile(json_path)):
            with open(json_path, "w") as f:
                f.write("[\n\n]")

    def dump(self, data):
        """ Dump data to a JSON file, checking for duplicates first

        Args:
            data: An iterable containing dictionaries to be dumped.
        """

        with open(self.json_path, "rb+") as f:
            if (len(data) > 0):
                f.seek(-2, os.SEEK_END)
                if (f.tell() != 2):
                    f.write(bytes(",\n", "UTF-8"))
                for _dict in data:
                    if (self.duplicate_checker.check(_dict["place_id"])):
                        f.write(bytes("%s,\n" % json.dumps(_dict), "UTF-8"))
                    else:
                        print("Ignoring duplicate %s" % _dict["place_id"])
                f.seek(-2, os.SEEK_END)
                f.write(bytes("\n]", "UTF-8"))
