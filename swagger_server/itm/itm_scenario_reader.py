import yaml
from typing import List, Tuple
from copy import deepcopy

from .itm_scene import ITMScene

from swagger_server.models import (
    ActionMapping,
    BaseState,
    BaseCharacter,
    BaseDemographics,
    BaseConditions,
    Event,
    Scenario,
    Scene,
    SemanticTypeEnum,
    ThreatState
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
        file.close()


    def read_scenario_from_yaml(self) -> Tuple[Scenario, List[ITMScene]]:
        """
        Generate a Scenario and its scenes from the YAML data.

        Returns:
            A tuple containing the generated Scenario and a list of ITMScenes.
        """
        state = self.generate_state(self.yaml_data['state'])
        scenes: List[ITMScene] = self.generate_scenes()

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


    def generate_scenes(self) ->  List[ITMScene]:
        scenes: List[ITMScene] = [
            self.generate_scene(scene_data)
            for scene_data in self.yaml_data['scenes']
        ]
        return scenes


    def convert_to_itmscene(self, scene: Scene) -> ITMScene:
        return ITMScene(scene)


    def generate_scene(self, scene_data) -> ITMScene:
        """
        Generate a Scene instance from the YAML data.

        Args:
            scene_data: The YAML data representing a scene.

        Returns:
            The ITMScene object to store scene details.
        """

        action_mapping = [
            self.generate_action_mapping(mapping_data)
            for mapping_data in scene_data['action_mapping']
        ]
        state = self.generate_state(scene_data.get('state'))
        scene = Scene(
            id=scene_data['id'],
            state=state,
            next_scene=scene_data.get('next_scene', ITMScene.END_SCENARIO_SENTINEL),
            end_scene_allowed=scene_data['end_scene_allowed'],
            persist_characters=scene_data.get('persist_characters', False),
            removed_characters=scene_data.get('removed_characters', []),
            probe_config=None, # Not used by TA3
            action_mapping=action_mapping,
            restricted_actions=scene_data.get('restricted_actions', []),
            transition_semantics=scene_data.get('transition_semantics', SemanticTypeEnum.AND),
            transitions=self.generate_conditions(scene_data.get('transitions'))
        )
        return self.convert_to_itmscene(scene)


    def generate_state(self, state_data) -> BaseState:
        if not state_data:
            return None
        unstructured = state_data.get('unstructured')
        threat_state = self.generate_threat_state(state_data)
        events = [
            self.generate_event(event_data)
            for event_data in state_data.get('events', [])
        ]
        characters = [
            self.generate_character(character_data)
            for character_data in state_data.get('characters', [])
        ]
        state = BaseState(
            unstructured=unstructured,
            elapsed_time=0,
            meta_info=None,
            scenario_complete=False,
            threat_state=threat_state,
            events=events,
            characters=characters
        )
        return state


    def generate_threat_state(self, state):
        threat_state = state.get('threat_state')
        if not threat_state:
            return None
        return ThreatState(
            unstructured=threat_state.get('unstructured'),
            threats=threat_state.get('threats')
        )


    def generate_event(self, event_data) -> Event:
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


    def generate_character(self, character_data) -> BaseCharacter:
        """
        Generate a character instance from the YAML data.

        Args:
            character_data: The YAML data representing a character.

        Returns:
            A character object representing the generated character.
        """
        demographics_data = character_data.get('demographics', {})
        demographics = BaseDemographics(
            age=demographics_data.get('age'),
            sex=demographics_data.get('sex', 'Unknown'),
            race=demographics_data.get('race', 'Unknown'),
            role=demographics_data.get('role')
        )
        character = BaseCharacter(
            id=character_data['id'],
            unstructured=character_data['unstructured'],
            name=character_data.get('name', 'Unknown'),
            rapport=character_data.get('rapport', 'neutral'),
            unseen=character_data.get('unseen', False),
            demographics=demographics
        )
        return character


    def generate_action_mapping(self, mapping_data) -> ActionMapping:
        if mapping_data is None:
            return None
        threat_state = self.generate_threat_state(mapping_data)
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
            action_conditions=self.generate_conditions(mapping_data.get('action_conditions')),
            probe_condition_semantics=mapping_data.get('probe_condition_semantics', SemanticTypeEnum.AND),
            probe_conditions=self.generate_conditions(mapping_data.get('probe_conditions'))
        )
        return mapping


    def generate_conditions(self, conditions_data) -> BaseConditions:
        if conditions_data is None:
            return None
        actions = []
        for action_list in conditions_data.get('actions', []):
            actions.append([action for action in action_list])
        probes = [probe for probe in conditions_data.get('probes', [])]
        probe_responses = [probe_response for probe_response in conditions_data.get('probe_responses', [])]
        conditions = BaseConditions(
            elapsed_time_gt=conditions_data.get('elapsed_time_gt'),
            elapsed_time_lt=conditions_data.get('elapsed_time_lt'),
            actions=actions,
            probes=probes,
            probe_responses=probe_responses
        )
        return conditions
