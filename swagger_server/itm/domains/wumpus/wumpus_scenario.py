from typing import List
from swagger_server.models import (
    State
)
from swagger_server.itm import ITMScenario


class WumpusScenario(ITMScenario):

    def __init__(self, yaml_path, session, ta1_name, training = False) -> None:
        super().__init__(yaml_path, session, ta1_name, training)


    @staticmethod
    def clear_hidden_data(state: State):
        for character in state.characters:
            if character.foobar:
                character.foobar = None

    def merge_state(self, current_state: State, target_state: State, previous_scene_characters: List):
        '''
        Merge domain-specific state from new scene into current state.  Approach:
        0. Abort if no state to merge
        1. Merge generic state (from parent class).
        2. For everything else, replace any specified (non-None) values.
        '''
        # Rule 0: Abort if no state to merge
        if not target_state:
            current_state.characters = []
            return

        # Rule 1. Merge generic state (from parent class).
        super().merge_state(current_state, target_state, previous_scene_characters)

        # Rule 2: For everything else, replace any specified (non-None) values.
        if target_state.foobar is not None:
            current_state.foobar = target_state.foobar
