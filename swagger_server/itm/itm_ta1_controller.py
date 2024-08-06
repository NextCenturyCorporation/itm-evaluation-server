import requests
import json
import os
import urllib
from swagger_server.models.probe_response import ProbeResponse  # noqa: F401,E501
from swagger_server.models.alignment_results import AlignmentResults  # noqa: F401,E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: F401,E501
from swagger_server import config_util


class ITMTa1Controller:
    
    config_util.check_ini()
    config = config_util.read_ini()[0]
    
    
    ADEPT_URL = config['DEFAULT']['ADEPT_URL']
    SOARTECH_URL = config['DEFAULT']['SOARTECH_URL']
    
    def __init__(self, alignment_target_id, scene_type, config, alignment_target = None):
        self.session_id = ''
        self.alignment_target_id = alignment_target_id
        self.alignment_target = alignment_target
        self.host_port = ITMTa1Controller.get_contact_info(scene_type=scene_type)

    @staticmethod
    def get_contact_info(scene_type):
        host_port = ITMTa1Controller.ADEPT_URL if scene_type == 'adept' else ITMTa1Controller.SOARTECH_URL
        # Technically this should never be hit since configs are mandatory but just in case
        if host_port is None or host_port == "":
            host_port = "localhost"
        return host_port
    @staticmethod
    def get_alignment_data(scene_type):
        host_port = ITMTa1Controller.get_contact_info(scene_type=scene_type)
        target_id_path = 'alignment_target_ids' if scene_type == 'adept' else 'alignment_targets'
        url = f"http://{host_port}/api/v1/{target_id_path}"
        alignment_target_ids = json.loads(requests.get(url).content.decode('utf-8'))
        alignments = []
        for alignment_target_id in alignment_target_ids:
          url = f"http://{host_port}/api/v1/alignment_target/{alignment_target_id}"
          alignment_target = json.loads(requests.get(url).content.decode('utf-8'))
          alignments.append(AlignmentTarget.from_dict(alignment_target))
        return alignments

    def to_dict(self, response):
        return json.loads(response.content.decode('utf-8'))

    def new_session(self, user_id=None):
        url = f"http://{self.host_port}/api/v1/new_session"
        if user_id:
            params = {"user_id": user_id}
            url = f"{url}?{urllib.parse.urlencode(params)}"
        initial_response = requests.post(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        self.session_id = response
        return response

    def post_probe(self, probe_response: ProbeResponse):
        body = {"session_id": self.session_id, "response": probe_response.to_dict()}
        url = f"http://{self.host_port}/api/v1/response"
        self.to_dict(requests.post(url, json=body))
        return None
    
    def get_probe_response_alignment(self, scenario_id, probe_id):
        base_url = f"http://{self.host_port}/api/v1/alignment/probe"
        session_id = self.session_id
        params = {
            "session_id": session_id,
            "target_id": self.alignment_target_id,
            "scenario_id": scenario_id,
            "probe_id": probe_id
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        initial_response = requests.get(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        return response

    def get_session_alignment(self, target_id = None):
        base_url = f"http://{self.host_port}/api/v1/alignment/session"
        params = {
            "session_id": self.session_id,
            "target_id": self.alignment_target_id if not target_id else target_id
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        initial_response = requests.get(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        return AlignmentResults.from_dict(response)
