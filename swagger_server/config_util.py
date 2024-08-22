import os
from os.path import exists
from configparser import ConfigParser
from dataclasses import dataclass
from typing import Optional

@dataclass
class config_data:
    success: bool
    data: dict
    source_path: Optional[str] = None

def read_ini(default_path='swagger_server/config.ini'):
    path = os.path.expanduser(default_path)
    parser = ConfigParser()
    parser.read(path)
    return (parser, path)

def check_ini():
    keys_values = {}
    parser_path = read_ini()
    ini = parser_path[0]
    final_path = parser_path[1]
    if exists(final_path):
        keys = ("EVALUATION_TYPE", "SCENARIO_DIRECTORY", "ADEPT_URL", "SOARTECH_URL", "SAVE_HISTORY", "SAVE_HISTORY_TO_S3", "HISTORY_DIRECTORY", "HISTORY_S3_BUCKET",
                "EVAL_NAME", "EVAL_NUMBER", "SOARTECH_EVAL_QOL_SCENARIOS", "SOARTECH_EVAL_VOL_SCENARIOS", "SOARTECH_TRAIN_QOL_SCENARIOS", "SOARTECH_TRAIN_VOL_SCENARIOS",
                "SOARTECH_QOL_ALIGNMENT_TARGETS", "SOARTECH_VOL_ALIGNMENT_TARGETS", "SOARTECH_EVAL_FILENAMES", "SOARTECH_TRAIN_FILENAMES")
        for option in keys:
            if option in ini["DEFAULT"]: # checks if "option" key exists in "default" section
                key_value = ini.get("DEFAULT", option)
                keys_values.setdefault(option, key_value)
            else: 
                raise Exception(f"Couldn't find key {option} in this file")
    else:
        raise FileNotFoundError(f"Couldn't find file: {os.path.abspath(final_path)}")
            
    return config_data(True, keys_values, final_path)

