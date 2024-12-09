import requests
import json
import urllib
import builtins
from swagger_server.models.probe_response import ProbeResponse  # noqa: F401,E501
from swagger_server.models.alignment_results import AlignmentResults  # noqa: F401,E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: F401,E501
from swagger_server.models.kdma_profile import KDMAProfile  # noqa: F401,E501
from swagger_server.models.kdma_value import KDMAValue  # noqa: F401,E501
from swagger_server import config_util


class ITMTa1Controller:
    config_util.check_ini()
    config = config_util.read_ini()[0]
    config_group = builtins.config_group

    ADEPT_URL = config[config_group]['ADEPT_URL']
    SOARTECH_URL = config[config_group]['SOARTECH_URL']
    ADEPT_MJ_ALIGNMENT_DISTRIBUTION_TARGET = config[config_group]['ADEPT_MJ_ALIGNMENT_DISTRIBUTION_TARGET']
    ADEPT_IO_ALIGNMENT_DISTRIBUTION_TARGET = config[config_group]['ADEPT_IO_ALIGNMENT_DISTRIBUTION_TARGET']

    def __init__(self, alignment_target_id, scene_type, alignment_target = None):
        self.session_id = ''
        self.alignment_target_id = alignment_target_id
        self.alignment_target = alignment_target
        self.scene_type = scene_type
        self.adept_populations = False
        self.url = ITMTa1Controller.get_contact_info(scene_type=scene_type)

    @staticmethod
    def get_contact_info(scene_type):
        host_port = ITMTa1Controller.ADEPT_URL if scene_type == 'adept' else ITMTa1Controller.SOARTECH_URL
        # Technically this `if` block should never evaluate to True since configs are mandatory, but just in case.
        if host_port is None or host_port == "":
            host_port = "localhost"
        return host_port

    @staticmethod
    def get_alignment_data(scene_type):
        host_port = ITMTa1Controller.get_contact_info(scene_type=scene_type)
        target_id_path = 'alignment_target_ids' if scene_type == 'adept' else 'alignment_targets'
        url = f"{host_port}/api/v1/{target_id_path}"
        alignment_target_ids = json.loads(requests.get(url).content.decode('utf-8'))
        alignments = []
        for alignment_target_id in alignment_target_ids:
          url = f"{host_port}/api/v1/alignment_target/{alignment_target_id}"
          response = requests.get(url)
          alignment_target = ITMTa1Controller.to_dict(response)
          alignments.append(AlignmentTarget.from_dict(alignment_target))
        return alignments

    @staticmethod
    def get_alignment_target_ids(scene_type):
        host_port = ITMTa1Controller.get_contact_info(scene_type=scene_type)
        target_id_path = 'alignment_target_ids' if scene_type == 'adept' else 'alignment_targets'
        url = f"{host_port}/api/v1/{target_id_path}"
        return json.loads(requests.get(url).content.decode('utf-8'))

    @staticmethod
    def get_alignment_target(scene_type, alignment_target_id):
        host_port = ITMTa1Controller.get_contact_info(scene_type=scene_type)
        url = f"{host_port}/api/v1/alignment_target/{alignment_target_id}"
        response = requests.get(url)
        alignment_target = ITMTa1Controller.to_dict(response)
        return AlignmentTarget.from_dict(alignment_target)

    @staticmethod
    def to_dict(response):
        return json.loads(response.content.decode('utf-8'))

    def new_session(self, user_id=None, adept_populations=False):
        url = f"{self.url}/api/v1/new_session"
        if user_id:
            params = {"user_id": user_id}
            url = f"{url}?{urllib.parse.urlencode(params)}"
        initial_response = requests.post(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        self.session_id = response
        self.adept_populations = adept_populations
        return response

    def post_probe(self, probe_response: ProbeResponse):
        body = {"session_id": self.session_id, "response": probe_response.to_dict()}
        url = f"{self.url}/api/v1/response"
        self.to_dict(requests.post(url, json=body))
        return None

    def get_probe_response_alignment(self, scenario_id, probe_id):
        base_url = f"{self.url}/api/v1/alignment/probe"
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
        if self.scene_type == 'adept' and self.adept_populations:
            base_url = f"{self.url}/api/v1/alignment/compare_sessions_population"
            actual_target_id = self.alignment_target_id if not target_id else target_id
            params = {
                "session_id_1_or_target_id": self.session_id,
                "session_id_2_or_target_id": actual_target_id,
                "target_pop_id": ITMTa1Controller.ADEPT_MJ_ALIGNMENT_DISTRIBUTION_TARGET if 'Moral' in actual_target_id \
                    else ITMTa1Controller.ADEPT_IO_ALIGNMENT_DISTRIBUTION_TARGET
            }
        else:
            base_url = f"{self.url}/api/v1/alignment/session"
            params = {
                "session_id": self.session_id,
                "target_id": self.alignment_target_id if not target_id else target_id
            }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        initial_response = requests.get(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        alignment_results :AlignmentResults = AlignmentResults.from_dict(response)

        # Need to get KDMAs from a separate endpoint.
        base_url = f"{self.url}/api/v1/computed_kdma_profile"
        params = {
            "session_id": self.session_id
        }
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        initial_response = requests.get(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        # KDMAs are represented slightly differently between the two TA1s.
        if self.scene_type == 'adept':
            kdmas = []
            for kdma_value in response:
                kdmas.append(KDMAValue.from_dict(kdma_value))
        else:
            kdma_profile :KDMAProfile = KDMAProfile.from_dict(response)
            kdmas = kdma_profile.computed_kdma_profile

        alignment_results.kdma_values = kdmas
        return alignment_results
