#!/usr/bin/env python3

import connexion
import os

from swagger_server import encoder

PORT = os.getenv("TA3_PORT")
if (PORT is None or PORT == ""):
    PORT = 8080

def main():
    app = connexion.App(__name__, specification_dir='../swagger/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'ITM TA3 API'}, pythonic_params=True)
    app.run(port=PORT)


if __name__ == '__main__':
    main()
