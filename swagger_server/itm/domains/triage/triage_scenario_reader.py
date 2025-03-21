from swagger_server.itm import (
    ITMScenarioReader,
    ITMScene
)
from .triage_scene import TriageScene

from swagger_server.models import (
    BaseState,
    BaseCharacter,
    BaseConditions,
    Character,
    Conditions,
    ConditionsCharacterVitals,
    DecisionEnvironment,
    Demographics,
    Environment,
    Injury,
    Mission,
    Scene,
    SimEnvironment,
    State,
    Supplies,
    Vitals
)


class TriageScenarioReader(ITMScenarioReader):
    """Class for converting YAML data to ITM scenarios in the Triage domain."""

    def __init__(self, yaml_path: str):
        """
        Initialize the class with YAML data from a file path.

        Args:
            yaml_path: The file path to the YAML data.
        """
        super().__init__(yaml_path)


    def convert_to_itmscene(self, scene: Scene) -> ITMScene:
        return TriageScene(scene)


    def generate_state(self, state_data) -> State:
        if not state_data:
            return None
        baseState: BaseState = super().generate_state(state_data)
        supplies = [
            self.generate_supplies(supply_data)
            for supply_data in state_data.get('supplies', [])
        ]
        state: State = State(
            unstructured=baseState.unstructured,
            elapsed_time=baseState.elapsed_time,
            meta_info=baseState.meta_info,
            events=baseState.events,
            threat_state=baseState.threat_state,
            characters=baseState.characters,
            scenario_complete=baseState.scenario_complete,
            mission=self.generate_mission(state_data),
            environment=self.generate_environment(state_data),
            supplies=supplies
        )
        return state


    def generate_mission(self, state) -> Mission:
        mission = state.get('mission')
        if not mission:
            return None
        character_importance = mission.get('character_importance', [])
        return Mission(
            unstructured=mission['unstructured'],
            mission_type=mission.get('mission_type'),
            character_importance=character_importance,
            civilian_presence=mission.get('civilian_presence'),
            communication_capability=mission.get('communication_capability'),
            roe=mission.get('roe'),
            political_climate=mission.get('political_climate'),
            medical_policies=mission.get('medical_policies')
        )


    def generate_environment(self, state) -> Environment:
        """
        Generate an Environment instance from the YAML data.

        Args:
            state: The YAML data representing the Environment.

        Returns:
            An Environment object representing the generated environment.
        """
        return Environment(
            sim_environment=self.generate_sim_environment(state),
            decision_environment=self.generate_decision_environment(state)
        ) if state.get('environment') else None


    def generate_sim_environment(self, state) -> SimEnvironment:
        """
        Generate a SimEnvironment instance from the YAML data.

        Args:
            state: The YAML data representing the sim environment.

        Returns:
            A SimEnvironment object representing the generated simulation environment.
        """
        environment = state['environment'].get('sim_environment', {})
        return SimEnvironment(
            type=environment.get('type'),
            weather=environment.get('weather'),
            terrain=environment.get('terrain'),
            flora=environment.get('flora'),
            fauna=environment.get('fauna'),
            temperature=environment.get('temperature'),
            humidity=environment.get('humidity'),
            lighting=environment.get('lighting'),
            visibility=environment.get('visibility'),
            noise_ambient=environment.get('noise_ambient'),
            noise_peak=environment.get('noise_peak')
        )


    def generate_decision_environment(self, state) -> DecisionEnvironment:
        """
        Generate a DecisionEnvironment instance from the YAML data.

        Args:
            state: The YAML data representing the decision environment.

        Returns:
            A DecisionEnvironment object representing the generated decision environment.
        """
        environment = state['environment'].get('decision_environment', {})
        return DecisionEnvironment(
            unstructured=environment.get('unstructured'),
            aid=environment.get('aid'),
            movement_restriction=environment.get('movement_restriction'),
            sound_restriction=environment.get('sound_restriction'),
            oxygen_levels=environment.get('oxygen_levels'),
            population_density=environment.get('population_density'),
            injury_triggers=environment.get('injury_triggers'),
            air_quality=environment.get('air_quality'),
            city_infrastructure=environment.get('city_infrastructure')
        )


    def generate_supplies(self, supply_data) -> Supplies:
        """
        Generate a Supplies instance from the YAML data.

        Args:
            supply_data: The YAML data representing a supply.

        Returns:
            A Supplies object representing the generated supply.
        """
        supplies = Supplies(
            type=supply_data['type'],
            reusable=supply_data.get('reusable', False),
            quantity=supply_data['quantity']
        )

        return supplies


    def generate_character(self, character_data) -> Character:
        """
        Generate a character instance from the YAML data.

        Args:
            character_data: The YAML data representing a character.

        Returns:
            A character object representing the generated character.
        """
        baseChar: BaseCharacter = super().generate_character(character_data)

        demographics_data = character_data.get('demographics', {})
        demographics: Demographics = Demographics(
            age=baseChar.demographics.age,
            sex=baseChar.demographics.sex,
            race=baseChar.demographics.race,
            role=baseChar.demographics.role,
            military_disposition=demographics_data.get('military_disposition'),
            military_branch=demographics_data.get('military_branch'),
            rank=demographics_data.get('rank'),
            rank_title=demographics_data.get('rank_title'),
            skills=demographics_data.get('skills'),
            mission_importance=demographics_data.get('mission_importance')
        )

        injuries = [
            Injury(
                name=injury['name'],
                location=injury.get('location'),
                severity=injury.get('severity'),
                source_character=injury.get('source_character'),
                treatments_required=injury.get('treatments_required', 1),
                # Uncomment if/when sim allows partial pre-treatment
                #treatments_applied=injury.get('treatments_applied', injury.get('treatments_required', 1)) if injury.get('status') == 'treated' else injury.get('treatments_applied', 0),
                treatments_applied=injury.get('treatments_applied', injury.get('treatments_required', 1)) if injury.get('status') == 'treated' else 0,
                status=injury.get('status', 'visible')
            )
            for injury in character_data.get('injuries', [])
        ]

        return Character(
            id=baseChar.id,
            name=baseChar.name,
            unstructured=baseChar.unstructured,
            demographics=demographics,
            rapport=baseChar.rapport,
            unseen=baseChar.unseen,
            unstructured_postassess=character_data.get('unstructured_postassess'),
            has_blanket=character_data.get('has_blanket', False),
            intent=character_data.get('intent'),
            directness_of_causality=character_data.get('directness_of_causality'),
            injuries=injuries,
            vitals=self.generate_vitals(character_data.get('vitals', {})),
            visited=character_data.get('visited', False),
            tag=character_data.get('tag')
        )


    def generate_vitals(self, vital_data) -> Vitals:
        if not vital_data:
            return None
        vitals = Vitals(
            avpu=vital_data.get('avpu'),
            ambulatory=vital_data.get('ambulatory'),
            mental_status=vital_data.get('mental_status'),
            breathing=vital_data.get('breathing'),
            heart_rate=vital_data.get('heart_rate'),
            triss=vital_data.get('triss'),
            spo2=vital_data.get('spo2')
        )
        return vitals


    def generate_conditions(self, conditions_data) -> Conditions:
        if conditions_data is None:
            return None
        baseConditions: BaseConditions = super().generate_conditions(conditions_data)

        character_vitals = [
            ConditionsCharacterVitals(
                character_id=char_vitals['character_id'],
                vitals=self.generate_vitals(char_vitals.get('vitals', {})),
            )
            for char_vitals in conditions_data.get('character_vitals', [])
        ]
        supplies = [
            self.generate_supplies(supply_data)
            for supply_data in conditions_data.get('supplies', [])
        ]
        return Conditions(
            elapsed_time_gt=baseConditions.elapsed_time_gt,
            elapsed_time_lt=baseConditions.elapsed_time_lt,
            actions=baseConditions.actions,
            probes=baseConditions.probes,
            probe_responses=baseConditions.probe_responses,
            character_vitals=character_vitals,
            supplies=supplies
        )
