#!/usr/bin/env python3

import connexion
import os
import argparse
import builtins
import sys
from swagger_server import config_util

from swagger_server import encoder

PORT = os.getenv("TA3_PORT")

if (PORT is None or PORT == ""):
    PORT = 8080

def main(args):

    itm_port = PORT if args.port == None else args.port
    itm_kwargs = {'title': 'ITM TA3 API'}

    builtins.config_group = args.config_group
    builtins.testing = args.testing
    builtins.max_sessions = args.max_sessions
    builtins.session_timeout = args.session_timeout

    app = connexion.App(__name__, specification_dir='../swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments=itm_kwargs, pythonic_params=True)
    app.run(port=itm_port)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Run the TA3 evaluation server',
        usage='python -m swagger_server [-h] [-c CONFIG_GROUP] [-p PORT] [-t] [--max_sessions MAX_SESSIONS] [--timeout SESSION_TIMEOUT]')
    parser.add_argument('-c', '--config_group', dest='config_group', type=str, default="DEFAULT",  help='Specify the configuration group in config.ini used to launch the Swagger server (default = DEFAULT)')
    parser.add_argument('-p', '--port', dest='port', type=int, default=None,  help='Specify the port the Swagger server will listen on (default = 8080)')
    parser.add_argument('-t', '--testing', action='store_true', default=False,
                        help='Put the server in test mode which will run standalone and not connect to TA1.')
    parser.add_argument('--max_sessions', dest='max_sessions', type=int, default=100, help='Hard maximum for number of simultaneous active sessions (default 100)')
    parser.add_argument('--timeout', dest='session_timeout', type=int, default=60, help="Number of minutes an ADM can be inactive before it's subject to being recycled (default 60)")
    args = parser.parse_args()

    #Checking for config_group in config.ini
    config = config_util.read_ini()[0]
    if args.config_group not in config:
        print(f"The Config Group `{args.config_group}` does not exist in config.ini.")
        sys.exit()
    if args.max_sessions < 1:
        print(f"The maximum number of sessions must be at least 1.")
        sys.exit()
    if args.session_timeout < 1:
        print(f"The session timeout must be at least 1 minute.")
        sys.exit()

    print("Swagger server launching with the `" + args.config_group + "` group (from config.ini)")


    main(args)
