import copy
import uuid
import yaml
from typing import List, Tuple

from .itm_casualty_simulator import CasualtySimulation
from .itm_supplies import ITMSupplies, SupplyDetails

from swagger_server.models.casualty import Casualty
from swagger_server.models.demographics import Demographics
from swagger_server.models.environment import Environment
from swagger_server.models.injury import Injury
from swagger_server.models.mission import Mission
from swagger_server.models.scenario import Scenario
from swagger_server.models.state import State
from swagger_server.models.supplies import Supplies
from swagger_server.models.threat_state import ThreatState
from swagger_server.models.triage_category import TriageCategory
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
            Tuple[Scenario, List[CasualtySimulation], List[ITMSupplies], SupplyDetails]:
        """
        Generate a Scenario and casualty simulations from the YAML data.

        Returns:
            A tuple containing the generated Scenario, a list of CasualtySimulation objects, and SupplysDetails objects.
        """
        state, casualty_simulations, supplies_details = self._generate_state()
        triage_categories = self._generate_triage_categories()

        id_actual = self.yaml_data['id']
        # id_generated = "scenario_" + str(uuid.uuid4())

        scenario = Scenario(
            id=id_actual,
            name=self.yaml_data['name'],
            start_time=str(0),
            state=state,
            triage_categories=triage_categories,
            session_complete=False
        )
        return (scenario, casualty_simulations, supplies_details)
    
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
        casualty_simulations = [
            self._generate_casualty_simulations(casualty_data)
            for casualty_data in state.get('casualties', [])
        ]
        state = State(
            unstructured=unstructured,
            elapsed_time=0,
            scenario_complete=False,
            mission=mission,
            environment=environment,
            threat_state=threat_state,
            supplies=supplies,
            casualties=[casualty.casualty for casualty in casualty_simulations]
        )
        return state, casualty_simulations, supplies_details

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

    def _generate_casualty(self, casualty_data) -> Casualty:
        """
        Generate a casualty instance from the YAML data.

        Args:
            casualty_data: The YAML data representing a casualty.

        Returns:
            A casualty object representing the generated casualty.
        """
        demograpics_data = casualty_data.get('demographics', {})
        demograpics = Demographics(
            age=demograpics_data.get('age'),
            sex=demograpics_data.get('sex'),
            rank=demograpics_data.get('rank')
        )
        injuries = [
            Injury(
                name=injury['name'],
                location=injury['location'],
                severity=injury['severity']
            )
            for injury in casualty_data.get('injuries', [])
        ]
        vital_data = casualty_data.get('vitals', {})
        vitals = Vitals(
            conscious=vital_data['conscious'],
            responsive=vital_data['responsive'],
            breathing=vital_data['breathing'],
            hrpmin=vital_data['hrpmin']
            #mm_hg=vital_data['mmHg'],
            #rr=vital_data['RR'],
            #sp_o2=vital_data['SpO2%'],
            #pain=vital_data['pain']
        )
        casualty = Casualty(
            id=casualty_data['id'], #"casualty_" + str(uuid.uuid4()),
            unstructured=casualty_data['unstructured'],
            name=casualty_data.get('name', 'Unknown'),
            demographics=demograpics,
            injuries=injuries,
            vitals=vitals,
            assessed=False,
            tag=None
        )
        return casualty

    def _generate_casualty_simulations(self, casualty_data) -> CasualtySimulation:
        """
        Generate a CasualtySimulation instance from the YAML data.

        Args:
            casualty_data: The YAML data representing a casualty simulation.

        Returns:
            A CasualtySimulation object representing the generated casualty simulation.
        """
        casualty = self._generate_casualty(casualty_data=casualty_data)
        #hidden_attributes = casualty_data.get('hidden_attributes', {})
        #vitals_changes = hidden_attributes.get('vitals_changes_over_time', {})
        casualty_simulation = CasualtySimulation(
            casualty=casualty
            # correct_tag=hidden_attributes.get('correct_tag'),
            # start_vitals=copy.deepcopy(casualty.vitals),
            # current_vitals=copy.deepcopy(casualty.vitals),
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
        return casualty_simulation


    def _generate_triage_categories(self) -> List[TriageCategory]:
        return [
            TriageCategory("MINIMAL", "", "")
        ]
