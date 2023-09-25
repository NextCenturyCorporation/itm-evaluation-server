from pymongo import MongoClient
from urllib.parse import quote_plus
import json
import os
from bson import ObjectId

class JSONEncoder(json.JSONEncoder):
    '''Custom JSON encoder that encodes MongoDB ObjectId instances as strings.'''
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


class MongoDB:
    def __init__(self, username: str, password: str, host: str, port: str, database: str):
        """
        Initialize a MongoDB connection.

        Args:
            username: The username for the MongoDB connection.
            password: The password for the MongoDB connection.
            host: The host address of the MongoDB server.
            port: The port number of the MongoDB server.
            database: The name of the database to connect to.
        """
        username = quote_plus(username)
        password = quote_plus(password)
        self.client = MongoClient(f'mongodb://{username}:{password}@{host}:{port}/')
        self.db = self.client[database]

    def insert_data(self, collection: str, data: dict) -> str:
        """
        Insert data into a MongoDB collection.

        Args:
            collection: The name of the collection to insert the data into.
            data: The data to be inserted into the collection.

        Returns:
            The inserted ID of the document.
        """
        result = self.db[collection].insert_one(data)
        return str(result.inserted_id)

    def retrieve_data(self, collection: str, object_id: str) -> dict:
        """
        Retrieve data from a MongoDB collection based on the object ID.

        Args:
            collection: The name of the collection to retrieve data from.
            object_id: The ID of the document to retrieve.

        Returns:
            The retrieved data as a dictionary.
        """
        retrieved_data = self.db[collection].find_one({"_id": ObjectId(object_id)})
        return retrieved_data

    def write_to_json_file(self, data: dict) -> None:
        """
        Write data to a JSON file.

        Args:
            data: The data to be written to the JSON file.

        Returns:
            None.
        """
        # Convert the ObjectId back to string if necessary
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, ObjectId):
                    data[k] = str(v)

        filepath = 'itm_db_local_output/'

        # Make directory if it doesn't exist
        os.makedirs(filepath, exist_ok=True)

        # Get the list of all json files in directory
        file_list = [f for f in os.listdir(filepath) if os.path.isfile(os.path.join(filepath, f)) and f.endswith('.json')]

        # Calculate file_number based on the number of files
        file_number = len(file_list) + 1
        file_name = f'itm_db_output_{file_number}.json'
        full_filepath = filepath + file_name

        with open(full_filepath, 'w') as f:
            # Convert Python dictionary to JSON and write to file
            json.dump(data, f, indent=4)

    def clear_database(self):
        # List all collections in the database
        collections = ['test', 'scenarios']
    
        # Loop through the collections and delete all documents
        for collection in collections:
            self.db[collection].delete_many({})
