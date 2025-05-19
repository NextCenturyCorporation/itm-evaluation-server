from swagger_server.itm import (
    ITMScenarioReader,
    ITMScene
)
from .p2triage_scene import P2TriageScene

from swagger_server.models import (
    BaseCharacter,
    Character,
    Scene
)


class P2TriageScenarioReader(ITMScenarioReader):
    """Class for converting YAML data to ITM scenarios in the p2triage domain."""

    def __init__(self, yaml_path: str):
        """
        Initialize the class with YAML data from a file path.

        Args:
            yaml_path: The file path to the YAML data.
        """
        super().__init__(yaml_path)


    def convert_to_itmscene(self, scene: Scene) -> ITMScene:
        return P2TriageScene(scene)


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
            medical_condition=character_data.get('medical_condition'),
            attribute=character_data.get('attribute')
        )
