import copy
import json
from inspect import signature
from typing import List
from swagger_server.models import (
    Scene, Action, ActionMapping, ActionTypeEnum, Conditions, SemanticTypeEnum, State
)

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
        if self.end_scene_allowed:
            actions.append(Action(action_id="end_scene_action", action_type='END_SCENE', unstructured="End the scene"))
        # TODO: Add unmapped actions that aren't restricted

        return actions


    def action_taken(self, action_id, justification, session_state):
        for mapping in self.action_mappings:
            if mapping.action_id == action_id:
                self.actions_taken.append(mapping.action_id)
                # Respond to probes if conditions are met.
                if self.conditions_met(mapping.conditions, session_state, mapping.condition_semantics):
                    self.parent_scenario.respond_to_probe(mapping.probe_id, mapping.choice, justification)
                # Determine if we should transition to the next scene.
                if self.conditions_met(self.transitions, session_state, self.transition_semantics):
                    self.parent_scenario.change_scene(mapping.next_scene, self.transitions)


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
                print(f'Returning true for action list {action_list}')
                return True
        return False


    # First returned value is whether to short-circuit conditions checking;
    # Second returned value is whether the condition was met
    # "not" semantics means that the overall condition is true if all of the conditions are false
    def _evaluate_condition(self, property, eval_function, prop_name, session_state, semantics):
        if property:
            condition_met = \
                eval_function(property) if len(signature(eval_function).parameters) == 1 \
                else eval_function(property, session_state)
            if condition_met:
                if semantics == SemanticTypeEnum.AND:
                    return False, True
                elif semantics == SemanticTypeEnum.OR:
                    print(f'returning true due to {prop_name} with "{semantics}" semantics')
                    return True, True
                else: # 'not'
                    print(f'returning false due to {prop_name} with "{semantics}" semantics')
                    return True, False
            else:
                if semantics == SemanticTypeEnum.AND:
                    print(f'returning false due to {prop_name} with "{semantics}" semantics')
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
        print(conditions)
        (short_circuit, probe_condition_met) = \
             self._evaluate_condition(conditions.probes, self._probe_condition_met, "probe_conditions", session_state, semantics)
        if short_circuit:
            return probe_condition_met
        (short_circuit, elapsed_gt_condition_met) = \
             self._evaluate_condition(conditions.elapsed_time_gt, self._elapsed_gt_condition_met, "elapsed_gt", session_state, semantics)
        if short_circuit:
            return elapsed_gt_condition_met
        (short_circuit, elapsed_lt_condition_met) = \
             self._evaluate_condition(conditions.elapsed_time_lt, self._elapsed_lt_condition_met, "elapsed_lt", session_state, semantics)
        if short_circuit:
            return elapsed_lt_condition_met
        (short_circuit, actions_condition_met) = \
             self._evaluate_condition(conditions.actions, self._actions_condition_met, "actions", session_state, semantics)
        if short_circuit:
            return actions_condition_met

        print(f'probe: {probe_condition_met}; gt: {elapsed_gt_condition_met}; lt: {elapsed_lt_condition_met}; actions: {actions_condition_met}')
        if (semantics == SemanticTypeEnum.AND):
            conditions_met = probe_condition_met and elapsed_gt_condition_met and elapsed_lt_condition_met and actions_condition_met
        elif (semantics == SemanticTypeEnum.OR):
            conditions_met = probe_condition_met  or elapsed_gt_condition_met  or elapsed_lt_condition_met  or actions_condition_met
        else: # "not" semantics means that the overall condition is true if all of the conditions are false
            conditions_met = not (probe_condition_met or elapsed_gt_condition_met or elapsed_lt_condition_met or actions_condition_met)
        print(f'returning {conditions_met} due to overall conditions with "{semantics}" semantics')
        return conditions_met
