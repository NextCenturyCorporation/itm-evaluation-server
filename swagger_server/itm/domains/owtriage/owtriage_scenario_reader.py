from swagger_server.itm import (
    ITMScenarioReader,
    ITMScene
)
from .owtriage_scene import OWTriageScene

from swagger_server.models import (
    BaseState,
    BaseCharacter,
    Character,
    Scene,
    State,
    Supplies,
    Vitals
)


class OWTriageScenarioReader(ITMScenarioReader):
    """Class for converting YAML data to ITM scenarios in the owtriage domain."""

    def __init__(self, yaml_path: str):
        """
        Initialize the class with YAML data from a file path.

        Args:
            yaml_path: The file path to the YAML data.
        """
        super().__init__(yaml_path)


    def set_first_scene_state(self, scenario, state, scenes):
        return # owtriage scenarios specify state for the first scene


    def convert_to_itmscene(self, scene: Scene) -> ITMScene:
        return OWTriageScene(scene)


    def generate_state(self, state_data) -> State:
        if not state_data:
            return None
        baseState: BaseState = super().generate_state(state_data)
        supplies = [
            self.generate_supply(supply_data)
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
            supplies=supplies
        )
        return state


    def generate_supply(self, supply_data) -> Supplies:
        """
        Generate a Supplies instance from the YAML data.

        Args:
            supply_data: The YAML data representing a supply.

        Returns:
            A Supplies object representing the generated supply.
        """
        supplies = Supplies(
            type=supply_data['type'],
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

        return Character(
            id=baseChar.id,
            name=baseChar.name,
            unstructured=baseChar.unstructured,
            demographics=baseChar.demographics,
            rapport=baseChar.rapport,
            unseen=baseChar.unseen,
            unstructured_near=character_data.get('unstructured_near'),
            unstructured_treated_near=character_data.get('unstructured_treated_near'),
            unstructured_far=character_data.get('unstructured_far'),
            unstructured_treated_far=character_data.get('unstructured_treated_far'),
            distance=character_data.get('distance', 0),
            nearby=character_data.get('nearby', True),
            treated=character_data.get('treated', False),
            tag=character_data.get('tag'),
            medical_condition=character_data.get('medical_condition'),
            attribute_rating=character_data.get('attribute_rating'),
            vitals=self.generate_vitals(character_data.get('vitals', {}))
        )


    def generate_vitals(self, vital_data) -> Vitals:
        if not vital_data:
            return None
        vitals = Vitals(
            avpu=vital_data.get('avpu'),
            breathing=vital_data.get('breathing'),
            heart_rate=vital_data.get('heart_rate')
        )
        return vitals
