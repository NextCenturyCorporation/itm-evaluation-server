import copy
import json
from random import shuffle
from inspect import signature
from typing import List
from swagger_server.models import (
    Scene, Action, ActionMapping, ActionTypeEnum, Conditions, SemanticTypeEnum, State
)
from swagger_server.util import get_swagger_class_enum_values

class ITMScene:
    """
    Class for managing a scene in the ITM system.
    """

    def __init__(self, scene :Scene):
        """
        Initialize an instance of ITMScene.
        """
        self.index = scene.index
        self.state :State = scene.state # State updates for the scene, including a new cast of characters
        self.end_scene_allowed = scene.end_scene_allowed
        self.action_mappings :List[ActionMapping] = scene.action_mapping
        for mapping in self.action_mappings:
            mapping.next_scene = self.index+1 if mapping.next_scene is None else mapping.next_scene
        self.actions_taken = []
        self.restricted_actions :List[ActionTypeEnum] = scene.restricted_actions
        self.transition_semantics :SemanticTypeEnum = scene.transition_semantics
        self.transitions :Conditions = scene.transitions
        self.training = False
        from .itm_scenario import ITMScenario
        self.parent_scenario :ITMScenario = None

    def to_obj(self, x :ActionMapping):
        '''
        Override method to pretty-print action mapping
        '''
        to_obj = {
            "action_id": x.action_id,
            "action_type": x.action_type,
            "unstructured": x.unstructured,
            "character_id": x.character_id,
            "probe_id": x.probe_id,
            "choice": x.choice,
            "parameters": x.parameters,
            "kdma_association": x.kdma_association,
            "conditions": json.loads(str(x.conditions).replace("'", '"').replace("None", '"None"')),
            "next_scene": x.next_scene
        }
        return to_obj

    def __str__(self):
        '''
        Override method to pretty-print itm scene
        '''
        action_mappings = []
        for x in self.action_mappings:
            action_mappings.append(self.to_obj(x))
        state_copy = {}
        if self.state:
            state_copy = copy.deepcopy(vars(self.state[0]))
            del state_copy['swagger_types']
            del state_copy['attribute_map']
            state_copy = str(state_copy).encode('utf-8').decode('unicode-escape').replace('"', "'")
        to_obj = {
            "index": self.index,
            "state": state_copy,
            "end_scene_allowed": self.end_scene_allowed,
            "action_mappings": action_mappings,
            "restricted_actions": self.restricted_actions,
            "transition_semantics": self.transition_semantics,
            "transitions": json.loads(str(self.transitions).replace('"', '').replace("'", '"').replace("None", '"None"').replace("False", "false").replace("True", "true"))
        }
        return json.dumps(to_obj, indent=4)


    def get_available_actions(self) -> List[Action]:
        actions :List[Action] = [
            Action(
                action_id=mapping.action_id,
                action_type=mapping.action_type,
                unstructured=mapping.unstructured,
                character_id=mapping.character_id,
                parameters=mapping.parameters,
                kdma_association=mapping.kdma_association if self.training else None
            )
            for mapping in self.action_mappings if (not mapping.action_id in self.actions_taken) or mapping.repeatable
        ]

        # Add unmapped action types (other than END_SCENE) that aren't explicitly restricted.
        valid_action_types = get_swagger_class_enum_values(ActionTypeEnum)
        valid_action_types.remove(ActionTypeEnum.END_SCENE)
        #TODO: uncomment when tagging configuration is supported (ITM-217)
        #valid_action_types.remove(ActionTypeEnum.TAG_CHARACTER)
        current_action_types = []
        for action in actions:
            current_action_types.append(action.action_type)
        new_action_types = \
            [action_type for action_type in valid_action_types if action_type not in current_action_types if action_type not in self.restricted_actions]
        for action_type in new_action_types:
            actions.append(Action(
                action_id=action_type.lower(),
                action_type=action_type,
                unstructured=action_type.replace('_', ' ')
            ))

        # Add "end scene" action if configured and not already added as an action mapping.
        if self.end_scene_allowed and ActionTypeEnum.END_SCENE not in current_action_types:
            actions.append(Action(action_id="end_scene_action", action_type=ActionTypeEnum.END_SCENE, unstructured="End the scene"))

        # Let's not be TOO predictable
        shuffle(actions)
        return actions


    def action_taken(self, action :Action, session_state :State):
        self.actions_taken.append(action.action_id)
        next_scene_index = self.index + 1
        for mapping in self.action_mappings:
            if mapping.action_id == action.action_id:
                next_scene_index = mapping.next_scene
                # Respond to probes if conditions are met.
                if self.conditions_met(mapping.conditions, session_state, mapping.condition_semantics):
                    self.parent_scenario.respond_to_probe(mapping.probe_id, mapping.choice, action.justification)
                break  # action_id's are unique within a scene

        # Determine if we should transition to the next scene.
        if action.action_type == ActionTypeEnum.END_SCENE or \
            self.conditions_met(self.transitions, session_state, self.transition_semantics):
                self.parent_scenario.change_scene(next_scene_index, self.transitions)

    def _probe_condition_met(self, probe_conditions :List[str]) -> bool:
        if not probe_conditions:
            return True
        return all(probe in self.parent_scenario.probes_sent for probe in probe_conditions)

    def _elapsed_gt_condition_met(self, elapsed_gt, session_state :State) -> bool:
        if elapsed_gt is None:
            return True
        return session_state.elapsed_time > elapsed_gt

    def _elapsed_lt_condition_met(self, elapsed_lt, session_state :State) -> bool:
        if elapsed_lt is None:
            return True
        return session_state.elapsed_time < elapsed_lt

    # Each list of actions is true if all specified actions have been taken.
    # Return True if the any of the specified lists of actions are true.
    # That is, multiple action lists have "or" semantics.
    def _actions_condition_met(self, actions_condition) -> bool:
        if not actions_condition:
            return True
        for action_list in actions_condition:
            if all(action in self.actions_taken for action in action_list):
                return True
        return False


    # First returned value is whether to short-circuit conditions checking;
    # Second returned value is whether the condition was met
    # "not" semantics means that the overall condition is true if all of the conditions are false
    def _evaluate_condition(self, property, eval_function, session_state, semantics):
        if property:
            condition_met = \
                eval_function(property) if len(signature(eval_function).parameters) == 1 \
                else eval_function(property, session_state)
            if condition_met:
                if semantics == SemanticTypeEnum.AND:
                    return False, True
                elif semantics == SemanticTypeEnum.OR:
                    return True, True
                else: # 'not'
                    return True, False
            else:
                if semantics == SemanticTypeEnum.AND:
                    return True, False
                if semantics == SemanticTypeEnum.OR:
                    return False, False
                else: # 'not'
                    return False, True

        # Lack of a property shouldn't make 'and' fail or 'or'/'not' succeed
        return False, semantics == SemanticTypeEnum.AND


    # TODO: implement based on all configurable conditions
    def conditions_met(self, conditions :Conditions, session_state: State, semantics) -> bool:
        if not conditions:
            return True

        (short_circuit, probe_condition_met) = \
             self._evaluate_condition(conditions.probes, self._probe_condition_met, session_state, semantics)
        if short_circuit:
            return probe_condition_met
        (short_circuit, elapsed_gt_condition_met) = \
             self._evaluate_condition(conditions.elapsed_time_gt, self._elapsed_gt_condition_met, session_state, semantics)
        if short_circuit:
            return elapsed_gt_condition_met
        (short_circuit, elapsed_lt_condition_met) = \
             self._evaluate_condition(conditions.elapsed_time_lt, self._elapsed_lt_condition_met, session_state, semantics)
        if short_circuit:
            return elapsed_lt_condition_met
        (short_circuit, actions_condition_met) = \
             self._evaluate_condition(conditions.actions, self._actions_condition_met, session_state, semantics)
        if short_circuit:
            return actions_condition_met

        if (semantics == SemanticTypeEnum.AND):
            conditions_met = probe_condition_met and elapsed_gt_condition_met and elapsed_lt_condition_met and actions_condition_met
        elif (semantics == SemanticTypeEnum.OR):
            conditions_met = probe_condition_met  or elapsed_gt_condition_met  or elapsed_lt_condition_met  or actions_condition_met
        else: # "not" semantics means that the overall condition is true if all of the conditions are false
            conditions_met = not (probe_condition_met or elapsed_gt_condition_met or elapsed_lt_condition_met or actions_condition_met)
        return conditions_met
