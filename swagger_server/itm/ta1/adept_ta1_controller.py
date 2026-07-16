import requests
import urllib
from swagger_server.models import KDMAValue
from .itm_ta1_controller import ITMTa1Controller, TA1Config
import re
import os
import logging
import builtins
from dataclasses import dataclass
from swagger_server.config_util import Configuration
from swagger_server.itm.utils import generate_list, resolve_tokens, load_scenario_ids, load_alignment_ids

scenarioRegex = re.compile(r'^ADEPT_(EVAL|TRAIN)_(?P<group>[^_]+)_SCENARIOS$', re.IGNORECASE)
targetRegex = re.compile(r'^ADEPT_(?P<group>[^_]+)_ALIGNMENT_TARGETS$', re.IGNORECASE)
distributionRegex = re.compile(r'^ADEPT_(?P<group>[^_]+)_ALIGNMENT_DISTRIBUTION_TARGET$', re.IGNORECASE)
testingMode = getattr(builtins, "testing", False)

@dataclass
class AdeptConfig(TA1Config):
    EVAL_FILENAMES: list
    TRAIN_FILENAMES: list
    evaluationScenarios: dict
    trainingScenarios: dict
    alignmentTargets: dict
    distributionTargets: dict
    target_to_group: dict


class AdeptTa1Controller(ITMTa1Controller):

    @classmethod
    def load_config(cls, config_group) -> AdeptConfig:
        if config_group not in cls.configurations.keys():
            cls.configurations[config_group] = cls.create_config(config_group)
        return cls.configurations[config_group]


    @classmethod
    def create_config(cls, config_group: str) -> TA1Config:
        logging.info('One-time ADEPT creation of %s configuration.', config_group)
        evaluationScenarios = {}
        trainingScenarios = {}
        alignmentTargets = {}
        distributionTargets = {}

        cfg = cls.config[config_group]
        scenario_directory = cfg['SCENARIO_DIRECTORY']
        logging.info("Scenario directory is %s.", scenario_directory)
        try:
            scenario_files = set(os.listdir(scenario_directory))
        except OSError:
            logging.fatal("Invalid filepath. Please check the SCENARIO_DIRECTORY variable in the config.ini file.")
            exit(1)

        scenario_ids = load_scenario_ids(scenario_directory, scenario_files)
        EVAL_FILENAMES = sorted(resolve_tokens(cfg['ADEPT_EVAL_FILENAMES'], scenario_files))
        TRAIN_FILENAMES = sorted(resolve_tokens(cfg['ADEPT_TRAIN_FILENAMES'], scenario_files))

        for key, value in cfg.items():
            if scenarioMatch := scenarioRegex.match(key):
                mode = scenarioMatch.group(1).lower()
                group = scenarioMatch.group('group').lower()
                correct_dict = evaluationScenarios if mode == 'eval' else trainingScenarios
                correct_dict[group] = resolve_tokens(value, scenario_ids)
            elif targetMatch := targetRegex.match(key):
                group = targetMatch.group('group').lower()
                tokens = sorted(generate_list(value))
                if testingMode:
                    suspects = [t for t in tokens if any(c in t for c in "*?[]()\\{\\}+^$|")]
                    if len(suspects) > 0:
                        logging.fatal("Found alignment target IDs suspected to be Glob or Regex patterns. These are not supported in testing mode and will likely cause a server crash.")
                    alignmentTargets[group] = tokens
                else:
                    alignmentTargets[group] = sorted(resolve_tokens(value, cls.alignment_ids))
            elif distributionMatch := distributionRegex.match(key):
                group = distributionMatch.group('group').lower()
                distributionTargets[group] = value.strip()

        target_to_group = {target: group for group, targets in alignmentTargets.items() for target in targets}

        ta1_config = AdeptConfig(ta1_name=cls.get_ta1name(),
                                 contact_url=cfg[f"{cls.get_ta1name().upper()}_URL"],
                                 EVAL_FILENAMES=EVAL_FILENAMES, TRAIN_FILENAMES=TRAIN_FILENAMES,
                                 evaluationScenarios=evaluationScenarios, trainingScenarios=trainingScenarios,
                                 alignmentTargets=alignmentTargets, distributionTargets=distributionTargets,
                                 target_to_group=target_to_group)
        return ta1_config


    # Static initialization, but also note call to init_config after the class definition
    configurations = {} # Maps configuration group strings to AdeptConfig objects
    config = None
    alignment_ids = None
    server_url = None


    @classmethod
    def init_config(cls):
        cls.config = Configuration.get_config()
        cls.server_url = cls.config[builtins.config_group][f"{cls.get_ta1name().upper()}_URL"]
        cls.alignment_ids = set() if testingMode else load_alignment_ids(cls.get_alignment_ids_path())
        logging.info("Loaded %d alignment ids from TA1 server.", len(cls.alignment_ids))
        cls.configurations[builtins.config_group] = AdeptTa1Controller.create_config(builtins.config_group)

    def __init__(self, config_group, alignment_target_id, alignment_target = None):
        super().__init__(alignment_target_id, alignment_target)
        self.adept_populations = False
        self.ta1_config = AdeptTa1Controller.load_config(config_group)

    @staticmethod
    def get_server_url() -> str:
        return AdeptTa1Controller.server_url

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
    def get_filenames(config_group, kdma_training) -> list[str]:
        ta1_config: AdeptConfig = AdeptTa1Controller.load_config(config_group)
        return ta1_config.TRAIN_FILENAMES if kdma_training else ta1_config.EVAL_FILENAMES

    @staticmethod
    def get_target_ids(config_group, itm_scenario) -> list[str]:
        ta1_config = AdeptTa1Controller.load_config(config_group)
        target_ids: list[str] = []
        source = ta1_config.trainingScenarios if itm_scenario.training else ta1_config.evaluationScenarios
        for group, scenarioList in source.items():
            if itm_scenario.id in scenarioList:
                target_ids.extend(ta1_config.alignmentTargets.get(group, ()))
        return target_ids

    def supports_probe_alignment(self) -> bool:
        #return not self.adept_populations
        return False # The above is technically right, but for expediency in Phase 2, set it to false to save TA1 round trips

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
            group = self.ta1_config.target_to_group.get(actual_target_id)
            if group:
                pop_id = self.ta1_config.distributionTargets.get(group)
                if pop_id:
                    params['target_pop_id'] = pop_id
        else:
            base_url = f"{self.url}/api/v1/alignment/session"
            params = {
                "session_id": self.session_id,
                "target_id": self.alignment_target_id if not target_id else target_id
            }
        return f"{base_url}?{urllib.parse.urlencode(params)}"


AdeptTa1Controller.init_config()
