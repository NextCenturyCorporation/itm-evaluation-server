from swagger_server.itm import (
    ITMActionHandler,
    ITMScenario,
    ITMScenarioReader,
    ITMSession
)

from .triage_action_handler import TriageActionHandler
from .triage_scenario import TriageScenario
from .triage_scenario_reader import TriageScenarioReader

class TriageConfig():
    # Implements the ITMDomainConfig protocol

    def get_domain_name(self) -> str:
        return 'triage'

    def get_action_handler(self, session: ITMSession) -> ITMActionHandler:
        return TriageActionHandler(session)

    def get_action_time_filespec(self) -> str:
        return 'swagger_server/itm/data/domains/triage/triageActionTimes.json'

    def get_scenario(self, yaml_path, session, ta1_name, training = False) -> ITMScenario:
        return TriageScenario(yaml_path, session, ta1_name, training)

    def get_scenario_reader(self, yaml_path: str) -> ITMScenarioReader:
        return TriageScenarioReader(yaml_path)
