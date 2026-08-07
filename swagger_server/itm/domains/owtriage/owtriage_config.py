from swagger_server.itm import (
    ITMActionHandler,
    ITMScenario,
    ITMScenarioReader,
    ITMSession
)

from .owtriage_action_handler import OWTriageActionHandler
from .owtriage_scenario import OWTriageScenario
from .owtriage_scenario_reader import OWTriageScenarioReader

class OwtriageConfig():
    # Implements the ITMDomainConfig protocol

    def get_domain_name(self) -> str:
        return 'owtriage'

    def get_action_handler(self, session: ITMSession) -> ITMActionHandler:
        return OWTriageActionHandler(session)

    def get_action_time_filespec(self) -> str:
        return 'swagger_server/itm/data/domains/owtriage/owtriageActionTimes.json'

    def get_scenario(self, yaml_path, session, ta1_name, training = False) -> ITMScenario:
        return OWTriageScenario(yaml_path, session, ta1_name, training)

    def get_scenario_reader(self, yaml_path: str) -> ITMScenarioReader:
        return OWTriageScenarioReader(yaml_path)
