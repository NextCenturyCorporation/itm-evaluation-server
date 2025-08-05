import requests
import urllib
from swagger_server.models import KDMAValue
from .itm_ta1_controller import ITMTa1Controller
import re
import os
import logging
import yaml
from swagger_server.itm.utils import generate_list, resolve_tokens

scenarioRegex = re.compile(r'^ADEPT_(EVAL|TRAIN)_(?P<group>[^_]+)_SCENARIOS$', re.IGNORECASE)
targetRegex = re.compile(r'^ADEPT_(?P<group>[^_]+)_ALIGNMENT_TARGETS$', re.IGNORECASE)
distributionRegex = re.compile(r'^ADEPT_(?P<group>[^_]+)_ALIGNMENT_DISTRIBUTION_TARGET$', re.IGNORECASE)

class AdeptTa1Controller(ITMTa1Controller):

    evaluationScenarios = {}
    trainingScenarios = {}
    alignmentTargets = {}
    distributionTargets = {}

    cfg = ITMTa1Controller.config[ITMTa1Controller.config_group]

    scenario_directory = cfg['SCENARIO_DIRECTORY']
    try:
        scenario_files = set(os.listdir(scenario_directory))
    except OSError:
        logging.fatal("Invalid filepath. Please check the SCENARIO_DIRECTORY variable in the config.ini file.")
        scenario_files = set()
    
    scenario_ids = set()
    for fname in scenario_files:
        if fname.endswith('.yaml'):
            path = os.path.join(scenario_directory, fname)
            try:
                with open(path, 'r') as f:
                    doc = yaml.safe_load(f)
                    scenario = doc.get('id')
                    if scenario:
                        scenario_ids.add(scenario)
            except Exception:
                pass

    ADEPT_EVAL_FILENAMES = resolve_tokens(cfg['ADEPT_EVAL_FILENAMES'], scenario_files)
    ADEPT_TRAIN_FILENAMES = resolve_tokens(cfg['ADEPT_TRAIN_FILENAMES'], scenario_files)

    for key, value in cfg.items():
        if scenarioMatch := scenarioRegex.match(key):
            mode = scenarioMatch.group(1).lower()
            group = scenarioMatch.group('group').lower()
            correct_dict = evaluationScenarios if mode == 'eval' else trainingScenarios
            correct_dict[group] = set(resolve_tokens(value, scenario_ids))
        elif targetMatch := targetRegex.match(key):
            group = targetMatch.group('group').lower()
            alignmentTargets[group] = generate_list(value)
        elif distributionMatch := distributionRegex.match(key):
            group = distributionMatch.group('group').lower()
            distributionTargets[group] = value.strip()
   
    target_to_group = {target: group for group, targets in alignmentTargets.items() for target in targets}
   
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
        source = AdeptTa1Controller.trainingScenarios if itm_scenario.training else AdeptTa1Controller.evaluationScenarios
        for group, scenarioList in source.items():
            if itm_scenario.id in scenarioList:
                target_ids.extend(AdeptTa1Controller.alignmentTargets.get(group, ()))
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
            group = AdeptTa1Controller.target_to_group.get(actual_target_id)
            if group:
                pop_id = AdeptTa1Controller.distributionTargets.get(group)
                if pop_id:
                    params['target_pop_id'] = pop_id
        else:
            base_url = f"{self.url}/api/v1/alignment/session"
            params = {
                "session_id": self.session_id,
                "target_id": self.alignment_target_id if not target_id else target_id
            }
        return f"{base_url}?{urllib.parse.urlencode(params)}"
