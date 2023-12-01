import copy
import yaml
from typing import List, Tuple

from .itm_character_simulator import CharacterSimulation
from .itm_supplies import ITMSupplies, SupplyDetails

from swagger_server.models.character import Character
from swagger_server.models.demographics import Demographics
from swagger_server.models.environment import Environment
from swagger_server.models.injury import Injury
from swagger_server.models.mission import Mission
from swagger_server.models.scenario import Scenario
from swagger_server.models.state import State
from swagger_server.models.supplies import Supplies
from swagger_server.models.threat_state import ThreatState
from swagger_server.models.vitals import Vitals


class ITMScenarioReader:
    """Class for converting YAML data to ITM scenarios."""

    def __init__(self, yaml_path: str):
        """
        Initialize the class with YAML data from a file path.

        Args:
            yaml_path: The file path to the YAML data.
        """
        with open(yaml_path, 'r') as file:
            self.yaml_data = yaml.safe_load(file)

    def read_scenario_from_yaml(self) -> \
            Tuple[Scenario, List[CharacterSimulation], List[ITMSupplies], SupplyDetails]:
        """
        Generate a Scenario and character simulations from the YAML data.

        Returns:
            A tuple containing the generated Scenario, a list of CharacterSimulation objects, and SupplysDetails objects.
        """
        state, character_simulations, supplies_details = self._generate_state()

        id_actual = self.yaml_data['id']

        scenario = Scenario(
            id=id_actual,
            name=self.yaml_data['name'],
            start_time=str(0),
            state=state,
            session_complete=False
        )
        return (scenario, character_simulations, supplies_details)
    
    def _generate_state(self):
        state = self.yaml_data['state']
        unstructured = state['unstructured']
        mission = self._generate_mission(state)
        environment = self._generate_environment(state)
        threat_state = self._generate_threat_state(state)
        supplies_details = ITMSupplies()
        supplies = [
            self._generate_supplies(supply_data, supplies_details)
            for supply_data in state.get('supplies', [])
        ]
        character_simulations = [
            self._generate_character_simulations(character_data)
            for character_data in state.get('characters', [])
        ]
        state = State(
            unstructured=unstructured,
            elapsed_time=0,
            scenario_complete=False,
            mission=mission,
            environment=environment,
            threat_state=threat_state,
            supplies=supplies,
            characters=[character.character for character in character_simulations]
        )
        return state, character_simulations, supplies_details

    def _generate_mission(self, state):
        mission = state['mission']
        return Mission(
            unstructured=mission['unstructured'],
            mission_type=mission['mission_type']
        )
    
    def _generate_environment(self, state) -> Environment:
        """
        Generate an Environment instance from the YAML data.

        Args:
            state: The YAML data representing the state.

        Returns:
            An Environment object representing the generated environment.
        """
        environment = state.get('environment', {})
        return Environment(
            unstructured=environment.get('unstructured'),
            weather=environment.get('weather'),
            location=environment.get('location'),
            terrain=environment.get('terrain'),
            flora=environment.get('flora'),
            fauna=environment.get('fauna'),
            soundscape=environment.get('soundscape'),
            aid_delay=environment.get('aid_delay'),
            temperature=environment.get('temperature'),
            humidity=environment.get('humidity'),
            lighting=environment.get('lighting'),
            visibility=environment.get('visibility'),
            noise_ambient=environment.get('noise_ambient'),
            noise_peak=environment.get('noise_peak')
        )
    
    def _generate_threat_state(self, state):
        threat_state = state['threat_state']
        return ThreatState(
            unstructured=threat_state['unstructured'],
            threats=threat_state['threats']
        )

    def _generate_supplies(self, supply_data, supply_details: ITMSupplies) -> Supplies:
        """
        Generate a Supplies instance from the YAML data.

        Args:
            supply_data: The YAML data representing a supply.
            supply_details: The ITMSupplies object to store supply details.

        Returns:
            A Supplies object representing the generated supply.
        """
        supplies = Supplies(
            type=supply_data['type'],
            quantity=supply_data['quantity']
        )
        
        hidden_attributes = supply_data.get('hidden_attributes', {})
        time_to_apply = hidden_attributes.get('time_to_apply_in_minutes')
        
        supply_details.get_supplies()[supplies.type] = SupplyDetails(
            supply=supplies,
            time_to_apply=time_to_apply
        )
        
        return supplies

    def _generate_character(self, character_data) -> Character:
        """
        Generate a character instance from the YAML data.

        Args:
            character_data: The YAML data representing a character.

        Returns:
            A character object representing the generated character.
        """
        demograpics_data = character_data.get('demographics', {})
        demograpics = Demographics(
            age=demograpics_data.get('age'),
            sex=demograpics_data.get('sex'),
            rank=demograpics_data.get('rank')
        )
        injuries = [
            Injury(
                name=injury['name'],
                location=injury.get('location'),
                severity=injury.get('severity')
            )
            for injury in character_data.get('injuries', [])
        ]
        vital_data = character_data.get('vitals', {})
        vitals = Vitals(
            conscious=vital_data['conscious'],
            mental_status=vital_data['mental_status'],
            breathing=vital_data['breathing'],
            hrpmin=vital_data['hrpmin']
            #mm_hg=vital_data['mmHg'],
            #rr=vital_data['RR'],
            #sp_o2=vital_data['SpO2%'],
        )
        character = Character(
            id=character_data['id'],
            unstructured=character_data['unstructured'],
            name=character_data.get('name', 'Unknown'),
            relationship=character_data.get('relationship', 'NONE'),
            demographics=demograpics,
            injuries=injuries,
            vitals=vitals,
            visited=False,
            tag=None
        )
        return character

    def _generate_character_simulations(self, character_data) -> CharacterSimulation:
        """
        Generate a CharacterSimulation instance from the YAML data.

        Args:
            character_data: The YAML data representing a character simulation.

        Returns:
            A CharacterSimulation object representing the generated character simulation.
        """
        character = self._generate_character(character_data=character_data)
        #hidden_attributes = character_data.get('hidden_attributes', {})
        #vitals_changes = hidden_attributes.get('vitals_changes_over_time', {})
        character_simulation = CharacterSimulation(
            character=character
            # correct_tag=hidden_attributes.get('correct_tag'),
            # start_vitals=copy.deepcopy(character.vitals),
            # current_vitals=copy.deepcopy(character.vitals),
            # treatments_applied=[],
            # treatments_needed=hidden_attributes.get('treatements_needed'),
            # hrpmin_change=vitals_changes.get('hrpmin'),
            # mmhg_change=vitals_changes.get('mmHg'),
            # rr_change=vitals_changes.get('RR'),
            # spo2_change=vitals_changes.get('SpO2%'),
            # stable=hidden_attributes.get('stable'),
            # deceased=hidden_attributes.get('deceased'),
            # deceased_after_minutes=hidden_attributes.get('deceased_after_minutes')
        )
        return character_simulation
