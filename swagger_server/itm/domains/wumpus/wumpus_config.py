from swagger_server.itm import (
    ITMActionHandler,
    ITMScenario,
    ITMScenarioReader,
    ITMSession
)

from .wumpus_action_handler import WumpusActionHandler
from .wumpus_scenario import WumpusScenario
from .wumpus_scenario_reader import WumpusScenarioReader

class WumpusConfig():
    # Implements the ITMDomainConfig protocol

    def get_domain_name(self) -> str:
        return 'wumpus'

    def get_action_handler(self, session: ITMSession) -> ITMActionHandler:
        return WumpusActionHandler(session)

    def get_action_time_filespec(self) -> str:
        return 'swagger_server/itm/data/domains/wumpus/wumpusActionTimes.json'

    def get_scenario(self, yaml_path, session, ta1_name, training = False) -> ITMScenario:
        return WumpusScenario(yaml_path, session, ta1_name, training)

    def get_scenario_reader(self, yaml_path: str) -> ITMScenarioReader:
        return WumpusScenarioReader(yaml_path)
