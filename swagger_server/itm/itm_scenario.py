from typing import List
from dataclasses import dataclass
from swagger_server.models import Scenario, Action
from .itm_character_simulator import ITMCharacterSimulator, CharacterSimulation
from .itm_scenario_reader import ITMScenarioReader
from .itm_scene import ITMScene
from .itm_alignment_target_reader import ITMAlignmentTargetReader
from .itm_ta1_controller import ITMTa1Controller

@dataclass
class ITMScenarioData:
    scenario: Scenario = None
    scenes: List[ITMScene] = None
    current_scene :ITMScene = None
    current_scene_index = 0
    alignment_target_reader: ITMAlignmentTargetReader = None
    character_simulations: List[CharacterSimulation] = None
    character_simulator: ITMCharacterSimulator = None
    hidden_injury_types = ['Burn'] # TBD: Hidden injuries should be configurable by type or injury instance
    ta1_controller: ITMTa1Controller = None

    # Pass-through to ITMScene
    def get_available_actions(self) -> List[Action]:
        return self.current_scene.get_available_actions()

class ITMScenario:

    def __init__(self, yaml_path, training = False) -> None:
        self.yaml_path = yaml_path
        self.scene_type = 'adept' if 'adept' in self.yaml_path else 'soartech'
        self.training = training
        self.isd :ITMScenarioData = None

    def generate_scenario_data(self):
        # isd is short for ITM Scenario Data
        isd = ITMScenarioData()

        scenario_reader = ITMScenarioReader(self.yaml_path + "scenario.yaml")
        ( isd.scenario, isd.scenes, isd.character_simulations) = \
            scenario_reader.read_scenario_from_yaml()
        isd.character_simulator = ITMCharacterSimulator()
        isd.character_simulator.setup_characters(isd.scenario, isd.character_simulations)

        if not self.training:
            isd.alignment_target_reader = ITMAlignmentTargetReader(self.yaml_path + "alignment_target.yaml")

        isd.ta1_controller = ITMTa1Controller(
            isd.alignment_target_reader.alignment_target.id if not self.training else None,
            self.scene_type
        )

        return isd
