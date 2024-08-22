import boto3
import json
import logging
import os
import time
import datetime

from botocore.exceptions import ClientError
from typing import Union

class ITMHistory:
    """
    Class for managing ADM action history.
    """

    def __init__(self, config):
        """
        Initialize an instance of ITMHistory.
        """
        self.history = []
        self.filepath = config["DEFAULT"]["HISTORY_DIRECTORY"] + os.sep
        self.save_history_bucket = config["DEFAULT"]["HISTORY_S3_BUCKET"]
        self.evaluation_info = {
            "evalName": config['DEFAULT']['EVAL_NAME'], 
            "evalNumber": config['DEFAULT']['EVAL_NUMBER'], 
            "created" : str(datetime.datetime.now())
        }        

    def clear_history(self):
        self.history.clear()

    def get_history(self):
        return self.history

    def add_history(self,
                    command: str,
                    parameters: dict,
                    response: Union[dict, str]) -> None:
        """
        Add a command to the history of the scenario session.

        Args:
            command: The command executed.
            parameters: The parameters passed to the command.
            response: The response from the command.
        """
        history_to_add = {
            "command": command,
            "parameters": parameters,
            "response": response
        }
        self.history.append(history_to_add)


    def write_to_json_file(self, filebasename, save_to_s3) -> None:
        """
        Write data to a JSON file.

        Args:
            data: The data to be written to the JSON file.

        Returns:
            None.
        """

        # Make directory if it doesn't exist
        os.makedirs(self.filepath, exist_ok=True)
        filespec = self.filepath + filebasename
        full_filepath = filespec + '.json'
        logging.info("Saving history to %s", full_filepath)

        with open(full_filepath, 'w') as file:
            # Convert Python dictionary to JSON and write to file
            json.dump({'evaluation': self.evaluation_info, 'history': self.history}, file, indent=2)

        if (save_to_s3):
            logging.info("Saving history to S3")
            if not self.save_json_to_s3(os.getcwd() + os.path.sep + full_filepath, filebasename  + '.json'):
                logging.warning("\033[92mUnable to save history to S3\033[00m")

    def save_json_to_s3(self, full_filepath, file_name) -> bool:
        """
        Copy file to S3

        Args:
            full_filepath: The file object to be copied to S3.
            file_name: File name, used as S3 object name.

        Returns:
            True if file was uploaded, else False
        """

        object_name = os.path.basename(file_name)

        # Upload the file
        s3_client = boto3.client('s3')
        try:
            s3_client.upload_file(full_filepath, self.save_history_bucket, object_name)
        except Exception:
            logging.exception("Could not save JSON to S3")
            return False
        return True