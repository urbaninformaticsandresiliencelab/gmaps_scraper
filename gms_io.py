#!/usr/bin/env python
# Library providing data dumping classes in a modular way for gmaps_scraper

# TODO: update documentation

import cPickle

try:
    import pymongo

    class MongoWriter(object):
        """ Handles writing to a MongoDB collection

        Attributes:
            collection: A pymongo.collection.Collection object to be written to.
        """

        def __init__(self, collection_name, db_name = "places_db",
                     host = "localhost:27017"):
            """ Initializes the MongoWriter class

            Args:
                db_name: A string containing the name of the database.
                collection_name: A string containing the name of the collection.
                host: A string containing the name of the host and its port.
            """

            self.collection = pymongo.MongoClient(host)[db_name][collection_name]

        def dump(self, data, dump_many = True):
            """ Write data to the previously defined collection

            Args:
                data: A dictionary object or iterable to be written to the
                    collection.
                dump_many: A boolean indicating whether or not data consists of
                    one dictionary or many dictionaries.
            """

            if (dump_many):
                self.collection.insert_many(data)
            else:
                self.collection.insert_one(data)

    try:
        import redis

        class MongoRedisWriter(MongoWriter):
            """ Child class of MongoWriter that handles writing to a MongoDB
            collection, checking against Redis for duplicates first

            Attributes:
                collection: A pymongo.collection.Collection object to be written
                    to.
                self.redis: A redis.StrictRedis instance that manages a
                    connection to the Redis server.
                self.redis_set: A string containing the name of the Redis set
                    that stores seen place_ids.
            """

            def __init__(self, mongo_collection_name,
                         mongo_db_name = "places_db",
                         redis_set = "seen_places", redis_db = 0,
                         mongo_host = "localhost:27017",
                         redis_host = "localhost", redis_port = 6379):
                """ Initializes the MongoWriter class

                Args:
                    mongo_db_name: A string containing the name of the MongoDB
                        database.
                    mongo_collection_name: A string containing the name of the
                        MongoDB collection.
                    redis_set: A string containing the name of the Redis set
                        that stores seen place_ids.
                    redis_db: An integer describing which Redis database to use.
                    mongo_host: A string containing the name of the MongoDB host
                        and its port.
                    redis_host: A string containing the name of the Redis host.
                    redis_port: An integer describing the port to use on the
                        Redis host.
                """

                MongoWriter.__init__(mongo_db_name, mongo_collection_name,
                                     mongo_host)
                self.redis = redis.StrictRedis(host = redis_host,
                                               port = redis_port, db = redis_db)
                self.redis_set = redis_set

            def add_dict(self, _dict):
                """ Add a dictionary to the MongoDB collection, checking for
                duplicates first

                Args:
                    _dict: A dictionary containing a Google Places API JSON.
                """
                place_id = _dict["place_id"]
                if (not self.redis.sismember(self.redis_set, place_id)):
                    self.redis.sadd(self.redis_set, place_id)
                    self.collection.insert_one(_dict)

            def dump(self, data, dump_many = True):
                """ Write data to the previously defined collection

                Args:
                    data: A dictionary object or iterable to be written to the
                        collection.
                    dump_many: A boolean indicating whether or not data consists
                        of one dictionary or many dictionaries.
                """
                if (dump_many):
                    for _dict in data:
                        add_dict(_dict)
                else:
                    add_dict(data)
    except:
        print("MongoRedisWriter class unavailable; redis not found")
except:
    print("MongoWriter class unavailable; pymongo not found")
    print("MongoRedisWriter class unavailable; parent class MongoWriter "
          "unavailable")

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
