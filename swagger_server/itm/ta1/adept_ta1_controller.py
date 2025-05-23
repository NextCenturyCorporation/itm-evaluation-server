import requests
import urllib
from swagger_server.models import KDMAValue
from .itm_ta1_controller import ITMTa1Controller


class AdeptTa1Controller(ITMTa1Controller):

    ADEPT_K1_ALIGNMENT_DISTRIBUTION_TARGET = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K1_ALIGNMENT_DISTRIBUTION_TARGET']
    ADEPT_K2_ALIGNMENT_DISTRIBUTION_TARGET = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K2_ALIGNMENT_DISTRIBUTION_TARGET']
    ADEPT_K3_ALIGNMENT_DISTRIBUTION_TARGET = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K3_ALIGNMENT_DISTRIBUTION_TARGET']
    ADEPT_K4_ALIGNMENT_DISTRIBUTION_TARGET = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K4_ALIGNMENT_DISTRIBUTION_TARGET']
    ADEPT_EVAL_FILENAMES = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_EVAL_FILENAMES'].replace('\n','').split(',')
    ADEPT_TRAIN_FILENAMES = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_TRAIN_FILENAMES'].replace('\n','').split(',')
    ADEPT_EVAL_K1_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_EVAL_K1_SCENARIOS'].replace('\n','').split(',')
    ADEPT_EVAL_K2_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_EVAL_K2_SCENARIOS'].replace('\n','').split(',')
    ADEPT_EVAL_K3_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_EVAL_K3_SCENARIOS'].replace('\n','').split(',')
    ADEPT_EVAL_K4_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_EVAL_K4_SCENARIOS'].replace('\n','').split(',')
    ADEPT_EVAL_M1_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_EVAL_M1_SCENARIOS'].replace('\n','').split(',')
    ADEPT_TRAIN_K1_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_TRAIN_K1_SCENARIOS'].replace('\n','').split(',')
    ADEPT_TRAIN_K2_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_TRAIN_K2_SCENARIOS'].replace('\n','').split(',')
    ADEPT_TRAIN_K3_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_TRAIN_K3_SCENARIOS'].replace('\n','').split(',')
    ADEPT_TRAIN_K4_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_TRAIN_K4_SCENARIOS'].replace('\n','').split(',')
    ADEPT_TRAIN_M1_SCENARIOS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_TRAIN_M1_SCENARIOS'].replace('\n','').split(',')
    ADEPT_K1_ALIGNMENT_TARGETS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K1_ALIGNMENT_TARGETS'].replace('\n','').split(',')
    ADEPT_K2_ALIGNMENT_TARGETS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K2_ALIGNMENT_TARGETS'].replace('\n','').split(',')
    ADEPT_K3_ALIGNMENT_TARGETS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K3_ALIGNMENT_TARGETS'].replace('\n','').split(',')
    ADEPT_K4_ALIGNMENT_TARGETS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_K4_ALIGNMENT_TARGETS'].replace('\n','').split(',')
    ADEPT_M1_ALIGNMENT_TARGETS = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_M1_ALIGNMENT_TARGETS'].replace('\n','').split(',')

    def __init__(self, alignment_target_id, alignment_target = None):
        super().__init__(self.get_ta1name(), alignment_target_id, alignment_target)
        self.adept_populations = False

    @staticmethod
    def get_server_url() -> str:
        return ITMTa1Controller.get_contact_info(AdeptTa1Controller.get_ta1name())

    @staticmethod
    def get_ta1name() -> str:
        return 'adept'

    @staticmethod
    def get_alignment_ids_path() -> str:
        return f"{AdeptTa1Controller.get_server_url()}/api/v1/alignment_target_ids"

    @staticmethod
    def get_alignment_target_path(alignment_target_id: str) -> str:
          return f"{AdeptTa1Controller.get_server_url()}/api/v1/alignment_target/{alignment_target_id}"

    @staticmethod
    def get_filenames(kdma_training) -> list[str]:
        return AdeptTa1Controller.ADEPT_TRAIN_FILENAMES if kdma_training else AdeptTa1Controller.ADEPT_EVAL_FILENAMES

    @staticmethod
    def get_target_ids(itm_scenario) -> list[str]:
        target_ids: list[str] = []
        if itm_scenario.id in (AdeptTa1Controller.ADEPT_TRAIN_K1_SCENARIOS if itm_scenario.training else AdeptTa1Controller.ADEPT_EVAL_K1_SCENARIOS):
            target_ids.extend(AdeptTa1Controller.ADEPT_K1_ALIGNMENT_TARGETS)
        if itm_scenario.id in (AdeptTa1Controller.ADEPT_TRAIN_K2_SCENARIOS if itm_scenario.training else AdeptTa1Controller.ADEPT_EVAL_K2_SCENARIOS):
            target_ids.extend(AdeptTa1Controller.ADEPT_K2_ALIGNMENT_TARGETS)
        if itm_scenario.id in (AdeptTa1Controller.ADEPT_TRAIN_K3_SCENARIOS if itm_scenario.training else AdeptTa1Controller.ADEPT_EVAL_K3_SCENARIOS):
            target_ids.extend(AdeptTa1Controller.ADEPT_K3_ALIGNMENT_TARGETS)
        if itm_scenario.id in (AdeptTa1Controller.ADEPT_TRAIN_K4_SCENARIOS if itm_scenario.training else AdeptTa1Controller.ADEPT_EVAL_K4_SCENARIOS):
            target_ids.extend(AdeptTa1Controller.ADEPT_K4_ALIGNMENT_TARGETS)
        if itm_scenario.id in (AdeptTa1Controller.ADEPT_TRAIN_M1_SCENARIOS if itm_scenario.training else AdeptTa1Controller.ADEPT_EVAL_M1_SCENARIOS):
            target_ids.extend(AdeptTa1Controller.ADEPT_M1_ALIGNMENT_TARGETS)
        return target_ids

    def supports_probe_alignment(self) -> bool:
        return not self.adept_populations

    def new_session(self, context=None) -> any:
        url = f"{self.url}/api/v1/new_session"
        initial_response = requests.post(url)
        initial_response.raise_for_status()
        response = self.to_dict(initial_response)
        self.session_id = response
        self.adept_populations = context is None or context.lower() != 'false' # True unless specified as false
        return response

    @staticmethod
    def get_kdmas(response) -> any:
        kdmas = []
        for kdma_value in response:
            kdmas.append(KDMAValue.from_dict(kdma_value))
        return kdmas

    def get_session_alignment_path(self, target_id: str = None) -> str:
        if self.adept_populations:
            base_url = f"{self.url}/api/v1/alignment/compare_sessions_population"
            actual_target_id = self.alignment_target_id if not target_id else target_id
            params = {
                "session_id_1_or_target_id": self.session_id,
                "session_id_2_or_target_id": actual_target_id
            }
            # TODO: Refactor this to avoid hardcoding
            if 'Moral' in actual_target_id or 'merit' in actual_target_id:
                params['target_pop_id'] = self.ADEPT_K1_ALIGNMENT_DISTRIBUTION_TARGET
            elif 'Ingroup' in actual_target_id or 'affiliation' in actual_target_id:
                params['target_pop_id'] = self.ADEPT_K2_ALIGNMENT_DISTRIBUTION_TARGET
            elif 'search' in actual_target_id:
                params['target_pop_id'] = self.ADEPT_K3_ALIGNMENT_DISTRIBUTION_TARGET
            elif 'safety' in actual_target_id:
                params['target_pop_id'] = self.ADEPT_K4_ALIGNMENT_DISTRIBUTION_TARGET
        else:
            base_url = f"{self.url}/api/v1/alignment/session"
            params = {
                "session_id": self.session_id,
                "target_id": self.alignment_target_id if not target_id else target_id
            }
        return f"{base_url}?{urllib.parse.urlencode(params)}"
