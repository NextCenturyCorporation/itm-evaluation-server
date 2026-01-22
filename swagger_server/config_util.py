import os
from os.path import exists
from configparser import ConfigParser

class Configuration:
    _instance = None
    _config = None
    _filename = None

    @staticmethod
    def initialize(filename):
        if Configuration._instance is not None:
            raise RuntimeError("Configuration has already been initialized.")

        Configuration._config, Configuration._filename = Configuration._load_config(filename)
        Configuration._instance = Configuration()

    @staticmethod
    def _load_config(filename):
        final_path = os.path.expanduser(filename)
        config = ConfigParser()
        config.read(final_path)
        keys_values = {}
        if exists(final_path):
            required_config = config.get("DEFAULT", 'REQUIRED_CONFIG').replace(',','').split()
            for option in required_config:
                if option in config["DEFAULT"]: # checks if "option" key exists in "default" section
                    key_value = config.get("DEFAULT", option)
                    keys_values.setdefault(option, key_value)
                else:
                    raise Exception(f"Couldn't find key {option} in {final_path}")
        else:
            raise FileNotFoundError(f"Couldn't find file: {os.path.abspath(final_path)}")

        return config, final_path

    @staticmethod
    def get_config():
        if Configuration._config is None:
            raise RuntimeError("Configuration not initialized. Call Configuration.initialize first.")
        return Configuration._config

    @staticmethod
    def get_filename():
        if Configuration._filename is None:
            raise RuntimeError("Configuration not initialized. Call Configuration.initialize first.")
        return Configuration._filename
