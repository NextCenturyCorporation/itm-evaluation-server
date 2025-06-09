from swagger_server.itm import (
    ITMScenarioReader,
    ITMScene
)
from .wumpus_scene import WumpusScene

from swagger_server.models import (
    BaseState,
    BaseCharacter,
    BaseConditions,
    Character,
    Conditions,
    Demographics,
    Scene,
    State
)


class WumpusScenarioReader(ITMScenarioReader):
    """Class for converting YAML data to ITM scenarios in the Wumpus domain."""

    def __init__(self, yaml_path: str):
        """
        Initialize the class with YAML data from a file path.

        Args:
            yaml_path: The file path to the YAML data.
        """
        super().__init__(yaml_path)


    def convert_to_itmscene(self, scene: Scene) -> ITMScene:
        return WumpusScene(scene)


    def generate_state(self, state_data) -> State:
        if not state_data:
            return None
        baseState: BaseState = super().generate_state(state_data)
        state: State = State(
            unstructured=baseState.unstructured,
            elapsed_time=baseState.elapsed_time,
            meta_info=baseState.meta_info,
            events=baseState.events,
            foobar=state_data.get('foobar'),
            threat_state=baseState.threat_state,
            characters=baseState.characters,
            scenario_complete=baseState.scenario_complete
        )
        return state


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
            foobar=demographics_data.get('foobar')
        )

        return Character(
            id=baseChar.id,
            name=baseChar.name,
            unstructured=baseChar.unstructured,
            demographics=demographics,
            rapport=baseChar.rapport,
            unseen=baseChar.unseen,
            foobar=character_data.get('foobar')
        )


    def generate_conditions(self, conditions_data) -> Conditions:
        if conditions_data is None:
            return None
        baseConditions: BaseConditions = super().generate_conditions(conditions_data)

        return Conditions(
            elapsed_time_gt=baseConditions.elapsed_time_gt,
            elapsed_time_lt=baseConditions.elapsed_time_lt,
            actions=baseConditions.actions,
            probes=baseConditions.probes,
            probe_responses=baseConditions.probe_responses,
            foobar=conditions_data.get('foobar')
        )
