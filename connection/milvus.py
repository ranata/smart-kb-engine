from pymilvus import connections, db, Collection, utility
import configparser
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "../config/config.ini")

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

host = config.get("Milvus", "host")
port = config.get("Milvus", "port")

connections.connect(uri=host, port=port)


def create_or_load_db(db_name):
    try:
        if db_name not in db.list_database():
            db.create_database(db_name)
        db.using_database(db_name)
        return db_name
    except Exception as e:
        print(f"Vector db service not available:{e}")


def create_or_load_collection(collection_name, schema=None):
    collection = None

    if collection_name in utility.list_collections():
        collection = Collection(collection_name)
    else:
        if schema:
            collection = Collection(collection_name, schema, consistency_level="Strong")
            print(f"{collection_name} created")
        else:
            print("schema not provided for creating collection")

    return collection


def get_collections(dbname: str):
    create_or_load_db(dbname)
    return utility.list_collections()
