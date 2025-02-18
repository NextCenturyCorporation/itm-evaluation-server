import requests
import urllib
from swagger_server.models import KDMAProfile
from .itm_ta1_controller import ITMTa1Controller


class SoartechTA1Controller(ITMTa1Controller):

    SOARTECH_EVAL_FILENAMES = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_EVAL_FILENAMES'].replace('\n','').split(',')
    SOARTECH_TRAIN_FILENAMES = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_TRAIN_FILENAMES'].replace('\n','').split(',')
    SOARTECH_EVAL_QOL_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_EVAL_QOL_SCENARIOS'].replace('\n','').split(',')
    SOARTECH_EVAL_VOL_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_EVAL_VOL_SCENARIOS'].replace('\n','').split(',')
    SOARTECH_TRAIN_QOL_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_TRAIN_QOL_SCENARIOS'].replace('\n','').split(',')
    SOARTECH_TRAIN_VOL_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_TRAIN_VOL_SCENARIOS'].replace('\n','').split(',')
    SOARTECH_QOL_ALIGNMENT_TARGETS = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_QOL_ALIGNMENT_TARGETS'].replace('\n','').split(',')
    SOARTECH_VOL_ALIGNMENT_TARGETS = ITMTa1Controller.config[ITMTa1Controller.config_group]['SOARTECH_VOL_ALIGNMENT_TARGETS'].replace('\n','').split(',')

    def __init__(self, alignment_target_id, alignment_target = None):
        super().__init__(self.get_ta1name(), alignment_target_id, alignment_target)

    @staticmethod
    def get_server_url() -> str:
        return ITMTa1Controller.get_contact_info(SoartechTA1Controller.get_ta1name())

    @staticmethod
    def get_ta1name() -> str:
        return 'soartech'

    @staticmethod
    def get_alignment_ids_path() -> str:
        return f"{SoartechTA1Controller.get_server_url()}/api/v1/alignment_targets"

    @staticmethod
    def get_alignment_target_path(alignment_target_id: str) -> str:
          return f"{SoartechTA1Controller.get_server_url()}/api/v1/alignment_target/{alignment_target_id}"

    @staticmethod
    def get_filenames(kdma_training) -> list[str]:
        return SoartechTA1Controller.SOARTECH_TRAIN_FILENAMES if kdma_training else SoartechTA1Controller.SOARTECH_EVAL_FILENAMES

    @staticmethod
    def get_target_ids(itm_scenario) -> list[str]:
        target_ids: list[str] = []
        if itm_scenario.id in (SoartechTA1Controller.SOARTECH_TRAIN_QOL_SCENARIOS if itm_scenario.training else SoartechTA1Controller.SOARTECH_EVAL_QOL_SCENARIOS):
            target_ids.extend(SoartechTA1Controller.SOARTECH_QOL_ALIGNMENT_TARGETS)
        if itm_scenario.id in (SoartechTA1Controller.SOARTECH_TRAIN_VOL_SCENARIOS if itm_scenario.training else SoartechTA1Controller.SOARTECH_EVAL_VOL_SCENARIOS):
            target_ids.extend(SoartechTA1Controller.SOARTECH_VOL_ALIGNMENT_TARGETS)
        return target_ids

    def new_session(self, context=None) -> any:
        url = f"{self.url}/api/v1/new_session"
        if context:
            params = {"user_id": context}
            url = f"{url}?{urllib.parse.urlencode(params)}"
        initial_response = requests.post(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        self.session_id = response
        return response

    @staticmethod
    def get_kdmas(response) -> any:
        kdma_profile: KDMAProfile = KDMAProfile.from_dict(response)
        return kdma_profile.computed_kdma_profile

    def get_session_alignment_path(self, target_id: str = None) -> str:
        base_url = f"{self.url}/api/v1/alignment/session"
        params = {
            "session_id": self.session_id,
            "target_id": self.alignment_target_id if not target_id else target_id
        }
        return f"{base_url}?{urllib.parse.urlencode(params)}"
