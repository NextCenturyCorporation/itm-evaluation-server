from typing import List
from dataclasses import dataclass
from swagger_server.models import Scenario, Action, ProbeResponse
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

class ITMScenario:

    def __init__(self, yaml_path, session, training = False) -> None:
        self.yaml_path = yaml_path
        self.scene_type = 'adept' if 'adept' in self.yaml_path else 'soartech'
        self.training = training
        self.alignment_target_reader: ITMAlignmentTargetReader = None
        self.ta1_controller: ITMTa1Controller = None
        from.itm_session import ITMSession
        self.session :ITMSession = session
        self.isd :ITMScenarioData
        self.id=''

    def generate_scenario_data(self):
        # isd is short for ITM Scenario Data
        isd = ITMScenarioData()

        scenario_reader = ITMScenarioReader(self.yaml_path + "scenario.yaml")
        ( isd.scenario, isd.scenes) = \
            scenario_reader.read_scenario_from_yaml()
        isd.current_scene_index = 0
        isd.current_scene = isd.scenes[0]
        for scene in isd.scenes:
            scene.training = self.training
            scene.parent_scenario = self
        self.isd = isd
        self.id = isd.scenario.id

        if not self.training:
            self.alignment_target_reader = ITMAlignmentTargetReader(self.yaml_path + "alignment_target.yaml")

        if self.session.ta1_integration:
            self.ta1_controller = ITMTa1Controller(
                self.alignment_target_reader.alignment_target.id if not self.training else None,
                self.scene_type
            )

    # Pass-through to ITMScene
    def get_available_actions(self) -> List[Action]:
        return self.isd.current_scene.get_available_actions()


    def respond_to_probe(self, probe_id, choice_id, justification):
        """
        Respond to the specified probe with the specified choice and justification

        Args:
            probe_id: The TA1 id of the probe
            choice_id: The TA1 id of the choice the ADM made
            justification: the choice justification provided by the ADM, if any
        """
        response = ProbeResponse(scenario_id=self.id, probe_id=probe_id, choice=choice_id,
                                 justification = '' if justification is None else justification)
        self.session.history.add_history(
            "Respond to TA1 Probe",
            {"session_id": self.session.session_id, "scenario_id": response.scenario_id, "probe_id": response.probe_id,
             "choice": response.choice, "justification": response.justification},
             None
            )
        if self.ta1_controller:
            self.ta1_controller.post_probe(probe_response=response)
            # Get and log probe response alignment
            probe_response_alignment = \
                self.ta1_controller.get_probe_response_alignment(
                response.scenario_id,
                response.probe_id
            )
            self.session.history.add_history(
                "TA1 Probe Response Alignment",
                {"session_id": self.ta1_controller.session_id,
                "scenario_id": response.scenario_id,
                "target_id": self.ta1_controller.alignment_target_id,
                "probe_id": response.probe_id},
                probe_response_alignment
            )
        print(f"--> Responding to probe {response.probe_id} from scenario {response.scenario_id} with choice {response.choice}.")


    def change_scene(self, next_scene):
        if (next_scene >= len(self.isd.scenes)):
            print("--> WARNING: scene configuration issue; final scene should have no transitions to the next scene")
            return #TODO: Address this and/or End the scenario
        self.isd.current_scene_index = next_scene
        self.isd.current_scene = self.isd.scenes[next_scene]

        # TODO: Merge state from new scene into session.state
        self.session.state.characters = self.isd.current_scene.state.characters
