from swagger_server.itm import (
    ITMActionHandler,
    ITMScenario,
    ITMScenarioReader,
    ITMSession
)

from .p2triage_action_handler import P2TriageActionHandler
from .p2triage_scenario import P2triageScenario
from .p2triage_scenario_reader import P2TriageScenarioReader

class P2TriageConfig():
    # Implements the ITMDomainConfig protocol

    def get_domain_name(self) -> str:
        return 'p2triage'

    def get_action_handler(self, session: ITMSession) -> ITMActionHandler:
        return P2TriageActionHandler(session)

    def get_action_time_filespec(self) -> str:
        return 'swagger_server/itm/data/domains/p2triage/p2triageActionTimes.json'

    def get_scenario(self, yaml_path, session, ta1_name, training = False) -> ITMScenario:
        return P2triageScenario(yaml_path, session, ta1_name, training)

    def get_scenario_reader(self, yaml_path: str) -> ITMScenarioReader:
        return P2TriageScenarioReader(yaml_path)
