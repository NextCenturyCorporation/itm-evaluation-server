import requests
import json
import os
import urllib
from swagger_server.models.probe_response import ProbeResponse  # noqa: F401,E501

# TODO: Add ports to configuration
ADEPT_PORT = os.getenv("ADEPT_PORT")
if (ADEPT_PORT == None or ADEPT_PORT == ""):
    ADEPT_PORT = '8081'
SOARTECH_PORT = os.getenv("SOARTECH_PORT")
if (SOARTECH_PORT == None or SOARTECH_PORT == ""):
    SOARTECH_PORT = '8084'
AWS_HOSTED = os.getenv("AWS_RUN")
if (AWS_HOSTED == None or AWS_HOSTED == ""):
    AWS_HOSTED = False

class ITMTa1Controller:
    HOST = "localhost"
    def __init__(self, alignment_target_id, scene_type):
        self.session_id = ''
        self.alignment_target_id = alignment_target_id
        self.alignment_target_body = None
        self.port = ADEPT_PORT if scene_type == 'adept' else SOARTECH_PORT
        if AWS_HOSTED and scene_type == 'adept':
            self.HOST = os.getenv("ADEPT_HOSTNAME")
        if AWS_HOSTED and scene_type == 'soartech':
            self.HOST = os.getenv("SOARTECH_HOSTNAME")
    

    def to_dict(self, response):
        return json.loads(response.content.decode('utf-8'))

    def new_session(self):
        url = f"http://{self.HOST}:{self.port}/api/v1/new_session"
        response = self.to_dict(requests.post(url))
        self.session_id = response
        return response

    def get_alignment_target(self):
        url = f"http://{self.HOST}:{self.port}/api/v1/alignment_target/{self.alignment_target_id}"
        response = self.to_dict(requests.get(url))
        self.alignment_target_body = response
        return response

    def post_probe(self, probe_response: ProbeResponse):
        body = {"session_id": self.session_id, "response": probe_response.to_dict()}
        url = f"http://{self.HOST}:{self.port}/api/v1/response"
        self.to_dict(requests.post(url, json=body))
        return None
    
    def get_probe_response_alignment(self, scenario_id, probe_id):
        base_url = f"http://{self.HOST}:{self.port}/api/v1/alignment/probe"
        session_id = self.session_id
        params = {
            "session_id": session_id,
            "target_id": self.alignment_target_id,
            "scenario_id": scenario_id,
            "probe_id": probe_id
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.to_dict(requests.get(url))
        return response

    def get_session_alignment(self):
        base_url = f"http://{self.HOST}:{self.port}/api/v1/alignment/session"
        params = {
            "session_id": self.session_id,
            "target_id": self.alignment_target_id
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.to_dict(requests.get(url))
        return response
