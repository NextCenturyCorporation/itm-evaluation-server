import os
from os.path import exists
from configparser import ConfigParser

def read_ini(default_path='swagger_server/config.ini'):
    final_path = os.path.expanduser(default_path)
    parser = ConfigParser(os.environ)
    parser.read(final_path)
    keys_values = {}
    if exists(final_path):
        required_config = parser.get("DEFAULT", 'REQUIRED_CONFIG').replace(',','').split()
        for option in required_config:
            if option in parser["DEFAULT"]: # checks if "option" key exists in "default" section
                key_value = parser.get("DEFAULT", option)
                keys_values.setdefault(option, key_value)
            else: 
                raise Exception(f"Couldn't find key {option} in {final_path}")
    else:
        raise FileNotFoundError(f"Couldn't find file: {os.path.abspath(final_path)}")

    return (parser, final_path)
