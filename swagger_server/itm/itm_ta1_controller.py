import requests
import json
import os
import urllib
from swagger_server.models.probe_response import ProbeResponse  # noqa: F401,E501
from swagger_server.models.alignment_results import AlignmentResults  # noqa: F401,E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: F401,E501

class ITMTa1Controller:
    ADEPT_PORT = os.getenv("ADEPT_PORT")
    if (ADEPT_PORT is None or ADEPT_PORT == ""):
        ADEPT_PORT = '8081'
    SOARTECH_PORT = os.getenv("SOARTECH_PORT")
    if (SOARTECH_PORT is None or SOARTECH_PORT == ""):
        SOARTECH_PORT = '8084'

    def __init__(self, alignment_target_id, scene_type, alignment_target = None):
        self.session_id = ''
        self.alignment_target_id = alignment_target_id
        self.alignment_target = alignment_target
        self.host, self.port = ITMTa1Controller.get_contact_info(scene_type=scene_type)

    @staticmethod
    def get_contact_info(scene_type):
        port = ITMTa1Controller.ADEPT_PORT if scene_type == 'adept' else ITMTa1Controller.SOARTECH_PORT
        host =  os.getenv("ADEPT_HOSTNAME") if scene_type == 'adept' else os.getenv("SOARTECH_HOSTNAME")
        if host is None or host == "":
            host = "localhost"
        return host, port

    @staticmethod
    def get_alignment_data(scene_type):
        (host, port) = ITMTa1Controller.get_contact_info(scene_type=scene_type)
        target_id_path = 'alignment_target_ids' if scene_type == 'adept' else 'alignment_targets'
        url = f"http://{host}:{port}/api/v1/{target_id_path}"
        alignment_target_ids = json.loads(requests.get(url).content.decode('utf-8'))
        alignments = []
        for alignment_target_id in alignment_target_ids:
          url = f"http://{host}:{port}/api/v1/alignment_target/{alignment_target_id}"
          alignment_target = json.loads(requests.get(url).content.decode('utf-8'))
          alignments.append(AlignmentTarget.from_dict(alignment_target))
        return alignments

    def to_dict(self, response):
        return json.loads(response.content.decode('utf-8'))

    def new_session(self):
        url = f"http://{self.host}:{self.port}/api/v1/new_session"
        response = self.to_dict(requests.post(url))
        self.session_id = response
        return response

    def post_probe(self, probe_response: ProbeResponse):
        body = {"session_id": self.session_id, "response": probe_response.to_dict()}
        url = f"http://{self.host}:{self.port}/api/v1/response"
        self.to_dict(requests.post(url, json=body))
        return None
    
    def get_probe_response_alignment(self, scenario_id, probe_id):
        base_url = f"http://{self.host}:{self.port}/api/v1/alignment/probe"
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

    def get_session_alignment(self, target_id = None):
        base_url = f"http://{self.host}:{self.port}/api/v1/alignment/session"
        params = {
            "session_id": self.session_id,
            "target_id": self.alignment_target_id if not target_id else target_id
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        response = self.to_dict(requests.get(url))
        return AlignmentResults.from_dict(response)
