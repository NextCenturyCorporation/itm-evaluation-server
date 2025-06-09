import copy
import logging
from typing import List
from swagger_server.models import (
    ActionTypeEnum, Conditions, Scene, SemanticTypeEnum, State, Supplies, SupplyTypeEnum
)
from swagger_server.itm import ITMScene

class TriageScene(ITMScene):
    """
    Class for managing a triage scene in the ITM system.
    """

    def __init__(self, scene: Scene):
        """
        Initialize an instance of TriageScene.
        """
        super().__init__(scene)


    def get_valid_action_types(self, state: State):
        remaining_action_types = super().get_valid_action_types(state)
        # Remove MOVE_TO_EVAC if there is no evacuation available.
        if ActionTypeEnum.MOVE_TO_EVAC in remaining_action_types and \
            (state.environment.decision_environment is None or state.environment.decision_environment.aid is None \
            or state.environment.decision_environment.aid == []):
            remaining_action_types.remove(ActionTypeEnum.MOVE_TO_EVAC)

        # Don't add actions that require a pulse ox if there is no pulse ox available.
        if ActionTypeEnum.CHECK_BLOOD_OXYGEN in remaining_action_types:
            pulse_ox_available = any(
                supply.type == SupplyTypeEnum.PULSE_OXIMETER and supply.quantity >= 1
                for supply in state.supplies
            )
            if not pulse_ox_available:
                if ActionTypeEnum.CHECK_BLOOD_OXYGEN in remaining_action_types:
                    remaining_action_types.remove(ActionTypeEnum.CHECK_BLOOD_OXYGEN)

        return remaining_action_types


    # True if any of the specified supplies is <= the specified quantity
    def _supply_condition_met(self, supply_conditions: List[Supplies], session_state: State) -> bool:
        if not supply_conditions:
            return True
        supply_conditions_met = any(
            state_supply.quantity <= supply_condition.quantity
            for supply_condition in supply_conditions
            for state_supply in session_state.supplies
            if supply_condition.type == state_supply.type
        )
        return supply_conditions_met

    # True if all vitals values of the source are equal to the target
    def _vital_condition_met(self, source_vitals, target_vitals) -> bool:
        for attr in source_vitals.attribute_map.keys():
            target_value = getattr(target_vitals, attr)
            if target_value is not None:
                source_value = getattr(source_vitals, attr)
                numeric_vital = isinstance(target_value, (float, int))
                if (not numeric_vital) and (target_value != source_value) or \
                    numeric_vital and (target_value < source_value):
                    return False
        return True

    # True if the any of the specified collection of vital values have been met for the specified character_id
    # Each list entry is true if all vitals values have been met by the specified character_id
    def _vitals_condition_met(self, vital_conditions: List, session_state: State) -> bool:
        if not vital_conditions:
            return True
        for vital_condition in vital_conditions:
            # Find the character in both the session state and scene (template) state
            session_character = None
            for session_character_lcv in session_state.characters:
                if session_character_lcv.id == vital_condition.character_id:
                    session_character = session_character_lcv
                    break
            scene_character = None
            for scene_character_lcv in self.state.characters:
                if scene_character_lcv.id == vital_condition.character_id:
                    scene_character = scene_character_lcv
                    break
            if not session_character:
                logging.warning("\033[92mcharacter_vitals condition specified character %s that is not in the State\033[00m", vital_condition.character_id)
                return False
            if not scene_character:
                logging.warning("\033[92mcharacter_vitals condition specified character %s that is not in the Scene\033[00m", vital_condition.character_id)
                return False

            # Copy any undiscovered vitals from the scene (template) character's vitals
            source_vitals = copy.copy(session_character.vitals)
            for attr in source_vitals.attribute_map.keys():
                if getattr(source_vitals, attr) is None:
                    setattr(source_vitals, attr, getattr(scene_character.vitals, attr))
            # If a vital_condition evaluates to true, then entire character_vitals condition is true
            if self._vital_condition_met(source_vitals, vital_condition.vitals):
                return True
        return False


    def evaluate_domain_conditions(self, conditions: Conditions, semantics, session_state: State):
        (short_circuit, supply_condition_met) = \
             self._evaluate_condition(conditions.supplies, self._supply_condition_met, semantics, session_state)
        if short_circuit:
            return True, supply_condition_met
        (short_circuit, vitals_condition_met) = \
             self._evaluate_condition(conditions.character_vitals, self._vitals_condition_met, semantics, session_state)
        if short_circuit:
            return True, vitals_condition_met

        return False, semantics == SemanticTypeEnum.AND

