import yaml
from typing import List, Tuple
from copy import deepcopy

from .itm_scene import ITMScene

from swagger_server.models import (
    ActionMapping,
    Character,
    ConditionsCharacterVitals,
    Conditions,
    Demographics,
    Environment,
    Event,
    DecisionEnvironment,
    Environment,
    DecisionEnvironment,
    SimEnvironment,
    Injury,
    Mission,
    Scenario,
    SemanticTypeEnum,
    State,
    Scene,
    Supplies,
    ThreatState,
    Vitals
)


class ITMScenarioReader:
    """Class for converting YAML data to ITM scenarios."""

    def __init__(self, yaml_path: str):
        """
        Initialize the class with YAML data from a file path.

        Args:
            yaml_path: The file path to the YAML data.
        """
        with open(yaml_path, 'r', encoding='utf-8') as file:
            self.yaml_data = yaml.safe_load(file)

    def read_scenario_from_yaml(self) -> Tuple[Scenario, List[ITMScene]]:
        """
        Generate a Scenario and its scenes from the YAML data.

        Returns:
            A tuple containing the generated Scenario and a list of ITMScenes.
        """
        state = self._generate_state(self.yaml_data['state'])
        scenes: List[ITMScene] = self._generate_scenes()

        scenario = Scenario(
            id=self.yaml_data['id'],
            name=self.yaml_data['name'],
            first_scene=self.yaml_data.get('first_scene', scenes[0].id),
            scenes=None,
            state=state,
            session_complete=False
        )

        for scene in scenes:
            if scene.id == scenario.first_scene:
                scene.state = deepcopy(state)

        return (scenario, scenes)

    def _generate_scenes(self) ->  List[ITMScene]:
        scenes :List[ITMScene] = [
            self._generate_scene(scene_data)
            for scene_data in self.yaml_data['scenes']
        ]
        return scenes

    def _generate_scene(self, scene_data) -> ITMScene:
        """
        Generate a Scene instance from the YAML data.

        Args:
            scene_data: The YAML data representing a scene.

        Returns:
            The ITMScene object to store scene details.
        """

        action_mapping = [
            self._generate_action_mapping(mapping_data)
            for mapping_data in scene_data['action_mapping']
        ]
        state = self._generate_state(scene_data.get('state'))
        scene = Scene(
            id=scene_data['id'],
            state=state,
            next_scene=scene_data.get('next_scene', ITMScene.END_SCENARIO_SENTINEL),
            end_scene_allowed=scene_data['end_scene_allowed'],
            persist_characters=scene_data.get('persist_characters', False),
            removed_characters=scene_data.get('removed_characters', []),
            probe_config=None, # Not used by TA3
            tagging=self._generate_tagging(scene_data),
            action_mapping=action_mapping,
            restricted_actions=scene_data.get('restricted_actions', []),
            transition_semantics=scene_data.get('transition_semantics', SemanticTypeEnum.AND),
            transitions=self._generate_conditions(scene_data.get('transitions'))
        )
        return ITMScene(scene)

    def _generate_state(self, state_data):
        if not state_data:
            return None
        unstructured = state_data.get('unstructured')
        mission = self._generate_mission(state_data)
        environment = self._generate_environment(state_data)
        threat_state = self._generate_threat_state(state_data)
        events = [
            self._generate_event(event_data)
            for event_data in state_data.get('events', [])
        ]
        supplies = [
            self._generate_supplies(supply_data)
            for supply_data in state_data.get('supplies', [])
        ]
        characters = [
            self._generate_character(character_data)
            for character_data in state_data.get('characters', [])
        ]
        state = State(
            unstructured=unstructured,
            elapsed_time=0,
            meta_info=None,
            scenario_complete=False,
            mission=mission,
            environment=environment,
            threat_state=threat_state,
            events=events,
            supplies=supplies,
            characters=characters
        )
        return state

    def _generate_mission(self, state) -> Mission:
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

    def _generate_environment(self, state) -> Environment:
        """
        Generate an Environment instance from the YAML data.

        Args:
            state: The YAML data representing the Environment.

        Returns:
            An Environment object representing the generated environment.
        """
        return Environment(
            sim_environment=self._generate_sim_environment(state),
            decision_environment=self._generate_decision_environment(state)
        ) if state.get('environment') else None

    def _generate_sim_environment(self, state) -> SimEnvironment:
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

    def _generate_decision_environment(self, state) -> DecisionEnvironment:
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

    def _generate_threat_state(self, state):
        threat_state = state.get('threat_state')
        if not threat_state:
            return None
        return ThreatState(
            unstructured=threat_state.get('unstructured'),
            threats=threat_state.get('threats')
        )

    def _generate_event(self, event_data) -> Event:
        """
        Generate an Event instance from the YAML data.

        Args:
            event_data: The YAML data representing an event.

        Returns:
            An Event object representing the generated event.
        """
        event = Event(
            type=event_data['type'],
            unstructured=event_data['unstructured'],
            source=event_data.get('source'),
            object=event_data.get('object'),
            action_id=event_data.get('action_id'),
            relevant_state=event_data.get('relevant_state')
        )

        return event

    def _generate_supplies(self, supply_data) -> Supplies:
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

    def _generate_character(self, character_data) -> Character:
        """
        Generate a character instance from the YAML data.

        Args:
            character_data: The YAML data representing a character.

        Returns:
            A character object representing the generated character.
        """
        demographics_data = character_data.get('demographics', {})
        demographics = Demographics(
            age=demographics_data.get('age'),
            sex=demographics_data.get('sex', 'Unknown'),
            race=demographics_data.get('race', 'Unknown'),
            military_disposition=demographics_data.get('military_disposition'),
            military_branch=demographics_data.get('military_branch'),
            rank=demographics_data.get('rank'),
            rank_title=demographics_data.get('rank_title'),
            skills=demographics_data.get('skills'),
            role=demographics_data.get('role'),
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
        character = Character(
            id=character_data['id'],
            unstructured=character_data['unstructured'],
            unstructured_postassess=character_data.get('unstructured_postassess'),
            has_blanket=character_data.get('has_blanket', False),
            name=character_data.get('name', 'Unknown'),
            rapport=character_data.get('rapport', 'neutral'),
            unseen=character_data.get('unseen', False),
            demographics=demographics,
            injuries=injuries,
            vitals=self._generate_vitals(character_data.get('vitals', {})),
            visited=character_data.get('visited', False),
            intent=character_data.get('intent'),
            directness_of_causality=character_data.get('directness_of_causality'),
            tag=character_data.get('tag')
        )
        return character

    def _generate_vitals(self, vital_data) -> Vitals:
        if not vital_data:
            return None
        vitals = Vitals(
            avpu=vital_data.get('avpu'),
            ambulatory=vital_data.get('ambulatory'),
            mental_status=vital_data.get('mental_status'),
            breathing=vital_data.get('breathing'),
            heart_rate=vital_data.get('heart_rate'),
            spo2=vital_data.get('spo2')
        )
        return vitals

    def _generate_action_mapping(self, mapping_data) -> ActionMapping:
        if mapping_data is None:
            return None
        threat_state = self._generate_threat_state(mapping_data)
        mapping = ActionMapping(
            action_id=mapping_data['action_id'],
            action_type=mapping_data['action_type'],
            unstructured=mapping_data['unstructured'],
            repeatable=mapping_data.get('repeatable', False),
            character_id=mapping_data.get('character_id'),
            intent_action=mapping_data.get('intent_action', False),
            threat_state=threat_state,
            parameters=mapping_data.get('parameters'),
            probe_id=mapping_data['probe_id'],
            choice=mapping_data['choice'],
            next_scene=mapping_data.get('next_scene'),
            kdma_association=mapping_data.get('kdma_association'),
            action_condition_semantics=mapping_data.get('action_condition_semantics', SemanticTypeEnum.AND),
            action_conditions=self._generate_conditions(mapping_data.get('action_conditions')),
            probe_condition_semantics=mapping_data.get('probe_condition_semantics', SemanticTypeEnum.AND),
            probe_conditions=self._generate_conditions(mapping_data.get('probe_conditions'))
        )
        return mapping

    def _generate_conditions(self, conditions_data) -> Conditions:
        if conditions_data is None:
            return None
        actions = []
        for action_list in conditions_data.get('actions', []):
            actions.append([action for action in action_list])
        probes = [probe for probe in conditions_data.get('probes', [])]
        probe_responses = [probe_response for probe_response in conditions_data.get('probe_responses', [])]
        character_vitals = [
            ConditionsCharacterVitals(
                character_id=char_vitals['character_id'],
                vitals=self._generate_vitals(char_vitals.get('vitals', {})),
            )
            for char_vitals in conditions_data.get('character_vitals', [])
        ]
        supplies = [
            self._generate_supplies(supply_data)
            for supply_data in conditions_data.get('supplies', [])
        ]
        conditions = Conditions(
            elapsed_time_gt=conditions_data.get('elapsed_time_gt'),
            elapsed_time_lt=conditions_data.get('elapsed_time_lt'),
            actions=actions,
            probes=probes,
            probe_responses=probe_responses,
            character_vitals=character_vitals,
            supplies=supplies
        )
        return conditions

    # Deferred
    def _generate_tagging(self, scene_data):
        return None
