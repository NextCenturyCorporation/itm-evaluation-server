from typing import List
from dataclasses import dataclass
from swagger_server.models import (
    Scenario, State, Action, ProbeResponse
)
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

        '''
        Merge state from new scene into session.state.  Approach:
        1. Always replace entire `characters` structure.
        2. For `supplies`, add or update any specified supplies.
        3. For everything else, replace any specified (non-None) values
           3a. Lists are copied whole (e.g., `character_importance`, `aid_delay`, `threats`).
        '''
        current_state :State = self.session.state
        target_state :State = self.isd.current_scene.state
        # Rule 1: Always replace entire `characters` structure.
        current_state.characters = target_state.characters

        # Rule 2: For `supplies`, add or update any specified supplies.
        if target_state.supplies:
            target_types = []
            current_types = []
            for target_supply in target_state.supplies:
                target_types.append(target_supply.type)
                for current_supply in current_state.supplies:
                    current_types.append(current_supply.type)
                    if target_supply.type == current_supply.type:
                        current_supply.quantity = target_supply.quantity
                        current_supply.reusable = target_supply.reusable
            new_types = [new_type for new_type in target_types if new_type not in current_types]
            new_supplies = [new_supply for new_supply in target_state.supplies if new_supply.type in new_types]
            current_state.supplies.extend(new_supplies)

        # Rule 3: For everything else, replace any specified (non-None) values.
        # Lists are copied whole (e.g., `character_importance`, `aid_delay`, `threats`).

        # Top-level unstructured.
        if target_state.unstructured:
            current_state.unstructured = target_state.unstructured

        # Threat state
        if target_state.threat_state:
            target = target_state.threat_state
            current = current_state.threat_state
            if not current:
                current = target
            else:
                current.unstructured=target.unstructured if target.unstructured else current.unstructured
                current.threats = target.threats if target.threats else current.threats
            current_state.threat_state = current

        # Mission
        if target_state.mission:
            target = target_state.mission
            current = current_state.mission
            if not current:
                current = target
            else:
                current.unstructured=target.unstructured if target.unstructured else current.unstructured
                current.mission_type=target.mission_type if target.mission_type else current.mission_type
                current.character_importance=target.character_importance if target.character_importance else current.character_importance
                current.civilian_presence=target.civilian_presence if target.civilian_presence else current.civilian_presence
                current.communication_capability=target.communication_capability if target.communication_capability else current.communication_capability
                current.medical_policies=target.medical_policies if target.medical_policies else current.medical_policies
                current.political_climate=target.political_climate if target.political_climate else current.political_climate
                current.roe=target.roe if target.roe else current.roe
            current_state.mission = current

        # Simulation Environment
        if target_state.environment and target_state.environment.sim_environment:
            target = target_state.environment.sim_environment
            current = current_state.environment.sim_environment # Valid scenarios will have sim_environment
            current.unstructured=target.unstructured if target.unstructured else current.unstructured
            current.temperature=target.temperature if target.temperature else current.temperature
            current.terrain=target.terrain if target.terrain else current.terrain
            current.weather=target.weather if target.weather else current.weather
            current.lighting=target.lighting if target.lighting else current.lighting
            current.visibility=target.visibility if target.visibility else current.visibility
            current.noise_ambient=target.noise_ambient if target.noise_ambient else current.noise_ambient
            current.noise_peak=target.noise_peak if target.noise_peak else current.noise_peak
            current.temperature=target.temperature if target.temperature else current.temperature
            current.humidity=target.humidity if target.humidity else current.humidity
            current.flora=target.flora if target.flora else current.flora
            current.fauna=target.fauna if target.fauna else current.fauna
            current_state.environment.sim_environment = current

        # Decision Environment
        if target_state.environment and target_state.environment.decision_environment:
            target = target_state.environment.decision_environment
            current = current_state.environment.decision_environment
            if not current:
                current = target
            else:
                current.unstructured=target.unstructured if target.unstructured else current.unstructured
                current.aid_delay=target.aid_delay if target.aid_delay else current.aid_delay
                current.movement_restriction=target.movement_restriction if target.movement_restriction else current.movement_restriction
                current.sound_restriction=target.sound_restriction if target.sound_restriction else current.sound_restriction
                current.oxygen_levels=target.oxygen_levels if target.oxygen_levels else current.oxygen_levels
                current.population_density=target.population_density if target.population_density else current.population_density
                current.injury_triggers=target.injury_triggers if target.injury_triggers else current.injury_triggers
                current.air_quality=target.air_quality if target.air_quality else current.air_quality
                current.city_infrastructure=target.city_infrastructure if target.city_infrastructure else current.city_infrastructure
            current_state.environment.decision_environment = current
