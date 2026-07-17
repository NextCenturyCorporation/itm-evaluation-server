import requests
import urllib
import logging
import builtins
from dataclasses import dataclass
from swagger_server.config_util import Configuration
from swagger_server.models import KDMAProfile
from .itm_ta1_controller import ITMTa1Controller, TA1Config

@dataclass
class SoartechConfig(TA1Config):
    EVAL_FILENAMES: list
    TRAIN_FILENAMES: list
    eval_qol_scenarios: list
    eval_vol_scenarios: list
    train_qol_scenarios: list
    train_vol_scenarios: list
    qol_alignmentTargets: list
    vol_alignmentTargets: list


class SoartechTa1Controller(ITMTa1Controller):

    @classmethod
    def load_config(cls, config_group) -> SoartechConfig:
        if config_group not in cls.configurations.keys():
            cls.configurations[config_group] = cls.create_config(config_group)
        return cls.configurations[config_group]

    @classmethod
    def create_config(cls, config_group: str) -> TA1Config:
        logging.info('One-time Soartech creation of %s configuration.', config_group)

        cfg = cls.config[config_group]
        ta1_config = SoartechConfig(ta1_name=cls.get_ta1name(),
                                    EVAL_FILENAMES=cfg['SOARTECH_EVAL_FILENAMES'].replace('\n','').split(','),
                                    TRAIN_FILENAMES=cfg['SOARTECH_TRAIN_FILENAMES'].replace('\n','').split(','),
                                    eval_qol_scenarios=cfg['SOARTECH_EVAL_QOL_SCENARIOS'].replace('\n','').split(','),
                                    eval_vol_scenarios=cfg['SOARTECH_EVAL_VOL_SCENARIOS'].replace('\n','').split(','),
                                    train_qol_scenarios=cfg['SOARTECH_TRAIN_QOL_SCENARIOS'].replace('\n','').split(','),
                                    train_vol_scenarios=cfg['SOARTECH_TRAIN_VOL_SCENARIOS'].replace('\n','').split(','),
                                    qol_alignmentTargets=cfg['SOARTECH_QOL_ALIGNMENT_TARGETS'].replace('\n','').split(','),
                                    vol_alignmentTargets=cfg['SOARTECH_VOL_ALIGNMENT_TARGETS'].replace('\n','').split(',')
        )
        return ta1_config


    # Static initialization, but also note call to init_config after the class definition
    configurations = {} # Maps configuration group strings to AdeptConfig objects
    config = None
    server_url = None


    @classmethod
    def init_config(cls):
        cls.config = Configuration.get_config()
        cls.server_url = cls.config[builtins.config_group][f"{cls.get_ta1name().upper()}_URL"]
        cls.configurations[builtins.config_group] = SoartechTa1Controller.create_config(builtins.config_group)


    def __init__(self, config_group, alignment_target_id, alignment_target = None):
        super().__init__(self.get_ta1name(), alignment_target_id, alignment_target)
        self.ta1_config = SoartechTa1Controller.load_config(config_group)

    @staticmethod
    def get_server_url() -> str:
        return SoartechTa1Controller.server_url

    @staticmethod
    def get_ta1name() -> str:
        return 'soartech'

    @staticmethod
    def get_alignment_ids_path() -> str:
        return f"{SoartechTa1Controller.get_server_url()}/api/v1/alignment_targets"

    @staticmethod
    def get_alignment_target_path(alignment_target_id: str) -> str:
          return f"{SoartechTa1Controller.get_server_url()}/api/v1/alignment_target/{alignment_target_id}"

    @staticmethod
    def get_filenames(config_group, kdma_training) -> list[str]:
        ta1_config: SoartechConfig = SoartechConfig.load_config(config_group)
        return ta1_config.TRAIN_FILENAMES if kdma_training else ta1_config.EVAL_FILENAMES

    @staticmethod
    def get_target_ids(config_group, itm_scenario) -> list[str]:
        ta1_config: SoartechConfig = SoartechConfig.load_config(config_group)
        target_ids: list[str] = []
        if itm_scenario.id in (ta1_config.train_qol_scenarios if itm_scenario.training else ta1_config.eval_qol_scenarios):
            target_ids.extend(ta1_config.qol_alignmentTargets)
        if itm_scenario.id in (ta1_config.train_vol_scenarios if itm_scenario.training else ta1_config.eval_vol_scenarios):
            target_ids.extend(ta1_config.vol_alignmentTargets)
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


SoartechTa1Controller.init_config()
