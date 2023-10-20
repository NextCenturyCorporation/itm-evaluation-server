import json
import os
from typing import Union

class ITMHistory:
    """
    Class for managing ADM action history.
    """

    def __init__(self):
        """
        Initialize an instance of ITMSupplies.
        """
        self.history = []
        self.filepath = 'itm_db_local_output/'

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


    def write_to_json_file(self) -> None:
        """
        Write data to a JSON file.

        Args:
            data: The data to be written to the JSON file.

        Returns:
            None.
        """

        # Make directory if it doesn't exist
        os.makedirs(self.filepath, exist_ok=True)

        # Get the list of all json files in directory
        file_list = [f for f in os.listdir(self.filepath) if os.path.isfile(os.path.join(self.filepath, f)) and f.endswith('.json')]

        # Calculate file_number based on the number of files
        file_number = len(file_list) + 1
        file_name = f'itm_db_output_{file_number}.json'
        full_filepath = self.filepath + file_name

        with open(full_filepath, 'w') as file:
            # Convert Python dictionary to JSON and write to file
            json.dump({'history': self.history}, file, indent=2)
