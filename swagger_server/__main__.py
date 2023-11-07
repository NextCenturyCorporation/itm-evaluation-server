#!/usr/bin/env python3

from json import encoder
import connexion
import os

PORT = os.getenv("TA3_PORT")
if (PORT == None or PORT == ""):
    PORT = 8080

def main():
    app = connexion.App(__name__, specification_dir='../swagger/')
    app.app.json = encoder.JSONEncoder
    app.add_api('swagger.yaml', arguments={'title': 'ITM TA3 API'}, pythonic_params=True)
    app.run(port=PORT)


if __name__ == '__main__':
    main()
