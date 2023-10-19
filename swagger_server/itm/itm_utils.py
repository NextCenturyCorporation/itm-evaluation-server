"""
Utils
"""

from typing import Union

history = []

def __init__():
    history.clear()

def clear_history():
    history.clear()

def get_history():
    return history

def add_history(command: str,
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
    history.append(history_to_add)
