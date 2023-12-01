from time import time
from typing import List
from dataclasses import dataclass
from datetime import datetime
from swagger_server.models import Scenario
from .itm_character_simulator import ITMCharacterSimulator, CharacterSimulation
from .itm_probe_reader import ITMProbeReader
from .itm_supplies import ITMSupplies
from .itm_scenario_reader import ITMScenarioReader
from .itm_alignment_target_reader import ITMAlignmentTargetReader
from .itm_ta1_controller import ITMTa1Controller

@dataclass
class ITMSessionScenarioObject:
    scenario: Scenario = None
    scenario_reader: ITMScenarioReader = None
    probe_system: ITMProbeReader = None
    alignment_target_reader: ITMAlignmentTargetReader = None
    character_simulations: List[CharacterSimulation] = None
    character_simulator: ITMCharacterSimulator = None
    supplies: ITMSupplies = None
    hidden_injury_types = ['Burn'] # TBD: Hidden injuries should be configurable by type or injury instance
    ta1_controller: ITMTa1Controller = None

class ITMSessionScenarioObjectHandler:

    def __init__(self, yaml_path) -> None:
        self.yaml_path = yaml_path

    def generate_session_scenario_object(self):
        # isso is short for ITM Session Scenario Object
        isso = ITMSessionScenarioObject()

        isso.scenario_reader = ITMScenarioReader(self.yaml_path + "scenario.yaml")
        isso.probe_system = ITMProbeReader(self.yaml_path)
        isso.probe_system.scenario = isso.scenario
        ( isso.scenario, isso.character_simulations, isso.supplies_details ) = \
            isso.scenario_reader.read_scenario_from_yaml()
        isso.character_simulator = ITMCharacterSimulator()
        isso.character_simulator.setup_characters(isso.scenario, isso.character_simulations)

        isso.alignment_target_reader = ITMAlignmentTargetReader(self.yaml_path + "alignment_target.yaml")

        isso.scenario.start_time = datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f")

        scene_type = 'adept' if 'adept' in self.yaml_path else 'soartech'
        isso.ta1_controller = ITMTa1Controller(
            isso.alignment_target_reader.alignment_target.id,
            scene_type
        )

        return isso
