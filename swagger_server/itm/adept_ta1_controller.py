import requests
import urllib
from swagger_server.models import KDMAValue
from .itm_ta1_controller import ITMTa1Controller


class AdeptTA1Controller(ITMTa1Controller):

    ADEPT_MJ_ALIGNMENT_DISTRIBUTION_TARGET = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_MJ_ALIGNMENT_DISTRIBUTION_TARGET']
    ADEPT_IO_ALIGNMENT_DISTRIBUTION_TARGET = ITMTa1Controller.config[ITMTa1Controller.config_group]['ADEPT_IO_ALIGNMENT_DISTRIBUTION_TARGET']

    def __init__(self, alignment_target_id, alignment_target = None):
        super().__init__(self.get_ta1name(), alignment_target_id, alignment_target)
        self.adept_populations = False

    @staticmethod
    def get_server_url() -> str:
        return ITMTa1Controller.get_contact_info(AdeptTA1Controller.get_ta1name())

    @staticmethod
    def get_ta1name() -> str:
        return 'adept'

    @staticmethod
    def get_alignment_ids_path() -> str:
        return f"{AdeptTA1Controller.get_server_url()}/api/v1/alignment_target_ids"

    @staticmethod
    def get_alignment_target_path(alignment_target_id: str) -> str:
          return f"{AdeptTA1Controller.get_server_url()}/api/v1/alignment_target/{alignment_target_id}"

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

    def get_session_alignment_path(self, target_id :str = None) -> str:
        if self.adept_populations:
            base_url = f"{self.url}/api/v1/alignment/compare_sessions_population"
            actual_target_id = self.alignment_target_id if not target_id else target_id
            params = {
                "session_id_1_or_target_id": self.session_id,
                "session_id_2_or_target_id": actual_target_id,
                "target_pop_id": self.ADEPT_MJ_ALIGNMENT_DISTRIBUTION_TARGET if 'Moral' in actual_target_id \
                    else self.ADEPT_IO_ALIGNMENT_DISTRIBUTION_TARGET
            }
        else:
            base_url = f"{self.url}/api/v1/alignment/session"
            params = {
                "session_id": self.session_id,
                "target_id": self.alignment_target_id if not target_id else target_id
            }
        return f"{base_url}?{urllib.parse.urlencode(params)}"
