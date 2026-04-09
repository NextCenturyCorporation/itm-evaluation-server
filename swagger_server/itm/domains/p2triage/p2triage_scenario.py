from swagger_server.models import (
    State
)
from swagger_server.itm import ITMScenario


class P2triageScenario(ITMScenario):

    def __init__(self, yaml_path, session, ta1_name, training = False) -> None:
        super().__init__(yaml_path, session, ta1_name, training)


    @staticmethod
    def clear_hidden_data(state: State, training: bool):
        if not training:
            for character in state.characters:
                character.medical_condition = None
                character.attribute_rating = None

        for character in state.characters:
            character.unstructured_posttreatment = None
