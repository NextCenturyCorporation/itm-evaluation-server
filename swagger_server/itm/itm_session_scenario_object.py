from time import time
from typing import List
from dataclasses import dataclass
from datetime import datetime
from swagger_server.models import Scenario
from .itm_character_simulator import ITMCharacterSimulator, CharacterSimulation
from .itm_probe_reader import ITMProbeReader
from .itm_scenario_reader import ITMScenarioReader
from .itm_scene import ITMScene
from .itm_alignment_target_reader import ITMAlignmentTargetReader
from .itm_ta1_controller import ITMTa1Controller

@dataclass
class ITMSessionScenarioObject:
    scenario: Scenario = None
    scenes: List[ITMScene] = None
    scenario_reader: ITMScenarioReader = None
    probe_system: ITMProbeReader = None
    alignment_target_reader: ITMAlignmentTargetReader = None
    character_simulations: List[CharacterSimulation] = None
    character_simulator: ITMCharacterSimulator = None
    hidden_injury_types = ['Burn'] # TBD: Hidden injuries should be configurable by type or injury instance
    ta1_controller: ITMTa1Controller = None

class ITMSessionScenarioObjectHandler:

    def __init__(self, yaml_path, training = False) -> None:
        self.yaml_path = yaml_path
        self.scene_type = 'adept' if 'adept' in self.yaml_path else 'soartech'
        self.training = training

    def generate_session_scenario_object(self):
        # isso is short for ITM Session Scenario Object
        isso = ITMSessionScenarioObject()

        isso.scenario_reader = ITMScenarioReader(self.yaml_path + "scenario.yaml")
        isso.probe_system = ITMProbeReader(self.yaml_path)
        isso.probe_system.scenario = isso.scenario
        ( isso.scenario, isso.scenes, isso.character_simulations) = \
            isso.scenario_reader.read_scenario_from_yaml()
        print(isso.scenario)
        print('-------------')
        print(isso.scenes[0].scene)
        print('-------------')
        print(isso.scenes[1].scene)
        isso.character_simulator = ITMCharacterSimulator()
        isso.character_simulator.setup_characters(isso.scenario, isso.character_simulations)

        if not self.training:
            isso.alignment_target_reader = ITMAlignmentTargetReader(self.yaml_path + "alignment_target.yaml")

        isso.scenario.start_time = datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f")

        isso.ta1_controller = ITMTa1Controller(
            isso.alignment_target_reader.alignment_target.id if not self.training else None,
            self.scene_type
        )

        return isso
