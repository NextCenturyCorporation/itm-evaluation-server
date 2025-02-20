import requests
import json
import urllib
import builtins
from abc import ABC, abstractmethod
from importlib import import_module
from swagger_server.models import (
    ProbeResponse, AlignmentResults, AlignmentTarget
)
from swagger_server import config_util

class ITMTa1Controller(ABC):
    config_util.check_ini()
    config = config_util.read_ini()[0]
    config_group = builtins.config_group

    def __init__(self, scene_type: str, alignment_target_id, alignment_target = None):
        self.session_id = ''
        self.alignment_target_id = alignment_target_id
        self.alignment_target = alignment_target
        self.url = self.get_contact_info(scene_type)

    @staticmethod
    def create_controller(scene_type, alignment_target_id=None, alignment_target=None):
        try:
            klass: ITMTa1Controller = ITMTa1Controller.__get_static_ref(scene_type)
            instance = klass(alignment_target_id, alignment_target)
            return instance
        except (ImportError, AttributeError, TypeError) as e:
            print(f"Error instantiating '{scene_type}' TA1 controller from factory: {e}")
            return None

    @staticmethod
    def __get_static_ref(scene_type: str):
        module = import_module(f"swagger_server.itm.ta1.{scene_type}_ta1_controller")
        return getattr(module, f"{scene_type.capitalize()}Ta1Controller")

    @staticmethod
    def get_contact_info(ta1_name: str) -> str:
        url = ITMTa1Controller.config[ITMTa1Controller.config_group][f"{ta1_name.upper()}_URL"]
        # Technically this `if` block should never evaluate to True since configs are mandatory, but just in case.
        if url is None or url == "":
            url = "localhost"
        return url

    @staticmethod
    @abstractmethod
    def get_server_url() -> str:
        ...

    @staticmethod
    @abstractmethod
    def get_ta1name() -> str:
        ...

    @staticmethod
    @abstractmethod
    def get_alignment_ids_path() -> str:
        ...

    @staticmethod
    @abstractmethod
    def get_alignment_target_path(alignment_target_id: str) -> str:
        ...

    def supports_probe_alignment() -> bool:
        return True

    @abstractmethod
    def new_session(self, context=None) -> any:
        ...

    @abstractmethod
    def get_session_alignment_path(self, target_id: str = None) -> str:
        ...

    @staticmethod
    @abstractmethod
    def get_kdmas(response) -> any:
        ...

    @staticmethod
    @abstractmethod
    def get_filenames(kdma_training):
        ...

    @staticmethod
    def get_filenames(ta1_name, kdma_training):
        return ITMTa1Controller.__get_static_ref(ta1_name).get_filenames(kdma_training)

    @staticmethod
    @abstractmethod
    def get_target_ids(itm_scenario) -> list[str]:
        ...

    @staticmethod
    def get_target_ids(ta1_name: str, itm_scenario) -> list[str]:
        return ITMTa1Controller.__get_static_ref(ta1_name).get_target_ids(itm_scenario)

    # Note: this method is currently unused but remains valid from an API perspective; and we might want to use it someday.
    @staticmethod
    def get_alignment_data(scene_type):
        alignment_target_ids = ITMTa1Controller.get_alignment_target_ids(scene_type)
        alignments = []
        ta1_class: ITMTa1Controller = ITMTa1Controller.__get_static_ref(scene_type)
        for alignment_target_id in alignment_target_ids:
          url = ta1_class.get_alignment_target_path(alignment_target_id)
          response = requests.get(url)
          alignment_target = ITMTa1Controller.to_dict(response)
          alignments.append(AlignmentTarget.from_dict(alignment_target))
        return alignments

    @staticmethod
    def get_alignment_target_ids(scene_type):
        ta1_class: ITMTa1Controller = ITMTa1Controller.__get_static_ref(scene_type)
        url = ta1_class.get_alignment_ids_path()
        return json.loads(requests.get(url).content.decode('utf-8'))

    @staticmethod
    def get_alignment_target(scene_type, alignment_target_id):
        ta1_class: ITMTa1Controller = ITMTa1Controller.__get_static_ref(scene_type)
        url = ta1_class.get_alignment_target_path(alignment_target_id)
        response = requests.get(url)
        alignment_target = ITMTa1Controller.to_dict(response)
        return AlignmentTarget.from_dict(alignment_target)

    @staticmethod
    def to_dict(response):
        return json.loads(response.content.decode('utf-8'))

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
        url = self.get_session_alignment_path(target_id)
        initial_response = requests.get(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        alignment_results: AlignmentResults = AlignmentResults.from_dict(response)

        # Need to get KDMAs from a separate endpoint.
        alignment_results.kdma_values = self.get_kdmas(response)

        return alignment_results
