from typing import List
from dataclasses import dataclass
from swagger_server.models import Scenario, Action, ProbeResponse
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
    character_simulations: List[CharacterSimulation] = None
    character_simulator: ITMCharacterSimulator = None

class ITMScenario:

    def __init__(self, yaml_path, training = False) -> None:
        self.yaml_path = yaml_path
        self.scene_type = 'adept' if 'adept' in self.yaml_path else 'soartech'
        self.training = training
        self.alignment_target_reader: ITMAlignmentTargetReader = None
        self.ta1_controller: ITMTa1Controller = None
        self.isd :ITMScenarioData
        self.id=''

    def generate_scenario_data(self):
        # isd is short for ITM Scenario Data
        isd = ITMScenarioData()

        scenario_reader = ITMScenarioReader(self.yaml_path + "scenario.yaml")
        ( isd.scenario, isd.scenes, isd.character_simulations) = \
            scenario_reader.read_scenario_from_yaml()
        isd.character_simulator = ITMCharacterSimulator()
        isd.character_simulator.setup_characters(isd.scenario, isd.character_simulations)
        isd.current_scene_index = 0
        isd.current_scene = isd.scenes[0]
        for scene in isd.scenes:
            scene.training = self.training
            scene.parent_scenario = self
        self.isd = isd
        self.id = isd.scenario.id

        if not self.training:
            self.alignment_target_reader = ITMAlignmentTargetReader(self.yaml_path + "alignment_target.yaml")

        self.ta1_controller = ITMTa1Controller(
            self.alignment_target_reader.alignment_target.id if not self.training else None,
            self.scene_type
        )

    # Pass-through to ITMScene
    def get_available_actions(self) -> List[Action]:
        return self.isd.current_scene.get_available_actions()

    def respond_to_probe(self, probe_id, choice_id, justification):
        response = ProbeResponse(scenario_id=self.id, probe_id=probe_id, choice=choice_id,
                                 justification = '' if justification == None else justification)
        if self.ta1_controller:
            self.ta1_controller.post_probe(probe_response=response)
            # TODO: Log probe response, see ITMSession.respond_to_probe()

    def change_scene(self, next_scene):
        if (next_scene == len(self.isd.scenes)):
            print("--> WARNING: scene configuration issue; final scene should have no transitions to the next scene")
            return #TODO: Address this and/or End the scenario
        self.isd.current_scene_index = next_scene
        self.isd.current_scene = self.isd.scenes[next_scene]

        # TODO: Merge state from new scene into session.state