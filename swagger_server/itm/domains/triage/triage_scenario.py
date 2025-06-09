from copy import deepcopy
from typing import List
from swagger_server.models import (
    InjuryStatusEnum, State, Vitals
)
from swagger_server.itm import ITMScenario


class TriageScenario(ITMScenario):

    def __init__(self, yaml_path, session, ta1_name, training = False) -> None:
        super().__init__(yaml_path, session, ta1_name, training)


    # Hide vitals (if not already visited) and hidden injuries
    @staticmethod
    def clear_hidden_data(state: State, training: bool):
        for character in state.characters:
            if character.visited:
                character.injuries[:] = \
                    [injury for injury in character.injuries if injury.status != InjuryStatusEnum.HIDDEN]
            else:
                initially_hidden_injuries = [InjuryStatusEnum.HIDDEN, InjuryStatusEnum.DISCOVERABLE]
                character.injuries[:] = \
                    [injury for injury in character.injuries if injury.status not in initially_hidden_injuries]
                character.unstructured_postassess = None
                character.vitals = Vitals()
        for injury in character.injuries:
            injury.treatments_required = None


    def merge_state(self, current_state: State, target_state: State, previous_scene_characters: List):
        '''
        Merge domain-specific state from new scene into current state.  Approach:
        0. Abort if no state to merge
        1. Merge generic state (from parent class).
        2. For `supplies`, add or update any specified supplies.
        3. For everything else, replace any specified (non-None) values.
        '''
        # Rule 0: Abort if no state to merge
        if not target_state:
            current_state.characters = []
            return

        # Rule 1. Merge generic state (from parent class).
        super().merge_state(current_state, target_state, previous_scene_characters)

        # Rule 2: For `supplies`, add or update any specified supplies.
        if target_state.supplies:
            target_types = []
            current_types = []
            for target_supply in target_state.supplies:
                target_types.append(target_supply.type)
                for current_supply in current_state.supplies:
                    current_types.append(current_supply.type)
                    if target_supply.type == current_supply.type:
                        current_supply.quantity = target_supply.quantity
                        current_supply.reusable = target_supply.reusable
            new_types = [new_type for new_type in target_types if new_type not in current_types]
            new_supplies = [new_supply for new_supply in target_state.supplies if new_supply.type in new_types]
            current_state.supplies.extend(deepcopy(new_supplies))

        # Rule 3: For everything else, replace any specified (non-None) values.
        current_state.mission = self.update_property(current_state.mission, target_state.mission)
        if target_state.environment:
            current_state.environment.sim_environment = \
                self.update_property(current_state.environment.sim_environment, target_state.environment.sim_environment)
            current_state.environment.decision_environment = \
                self.update_property(current_state.environment.decision_environment, target_state.environment.decision_environment)
