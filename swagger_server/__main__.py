#!/usr/bin/env python3

import connexion
import os
import argparse
import builtins

from swagger_server import encoder

PORT = os.getenv("TA3_PORT")

if (PORT is None or PORT == ""):
    PORT = 8080

def main(args):

    itm_port = PORT if args.port == None else args.port
    itm_kwargs = {'config_group' : args.config_group, 'title': 'ITM TA3 API'}

    builtins.config_group = args.config_group

    app = connexion.App(__name__, specification_dir='../swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments=itm_kwargs, pythonic_params=True)
    app.run(port=itm_port)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Specify Config Group; will default to the DEFAULT group', usage='python -m swagger_server [-h] -c CONFIG_GROUP')
    parser.add_argument('-c', '--config_group', dest='config_group', type=str, default="DEFAULT",  help='Specify the configuration group in config.ini used to launch the swagger server (default = DEFAULT)')
    parser.add_argument('-p', '--port', dest='port', type=int, default=None,  help='Specify the port the Swagger Server will listen on (default = None)')
    args = parser.parse_args()
    print("Swagger Server launching with the `" + args.config_group + "` group (from config.ini)")
       
    main(args)
