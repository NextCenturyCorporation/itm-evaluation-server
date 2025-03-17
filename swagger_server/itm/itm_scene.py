import copy
import json
import logging
from random import shuffle
from inspect import signature
from typing import List
from swagger_server.models import (
    Action, ActionMapping, ActionTypeEnum, Conditions, Scene, SemanticTypeEnum, State
)
from swagger_server.util import get_swagger_class_enum_values

class ITMScene:
    """
    Class for managing a scene in the ITM system.
    """

    # Denotes that the scenario should end after this scene
    END_SCENARIO_SENTINEL = '__END_SCENARIO__'

    def __init__(self, scene: Scene):
        """
        Initialize an instance of ITMScene.
        """
        self.id = scene.id
        self.state: State = scene.state # State updates for the scene, including a new cast of characters
        self.end_scene_allowed = scene.end_scene_allowed
        self.persist_characters = scene.persist_characters
        self.removed_characters = scene.removed_characters
        self.action_mappings: List[ActionMapping] = scene.action_mapping
        self.actions_taken = []
        self.restricted_actions: List[ActionTypeEnum] = scene.restricted_actions
        self.transition_semantics: SemanticTypeEnum = scene.transition_semantics
        self.transitions: Conditions = scene.transitions
        self.training = False
        from .itm_scenario import ITMScenario
        self.parent_scenario: ITMScenario = None

        logging.debug('--> Setting next scenes for scene %s.', self.id)
        # Initialize action mapping next scenes, relying on scene-level default if necessary
        if isinstance(self.id, int) and self.id >= 0: # ids are simple indices
            self.default_next_scene = self.id + 1
        else:
            self.default_next_scene = scene.next_scene
        for mapping in self.action_mappings:
            if mapping.action_type == 'END_SCENE':
                self.end_scene_allowed = True
            if mapping.next_scene is None or mapping.next_scene == '':
                mapping.next_scene = self.default_next_scene # if not specified in action mapping, inherit from scene
            logging.debug('mapping id %s has next scene of %s.', mapping.action_id, mapping.next_scene)


    def to_obj(self, x: ActionMapping):
        '''
        Override method to pretty-print action mapping
        '''
        to_obj = {
            "action_id": x.action_id,
            "action_type": x.action_type,
            "unstructured": x.unstructured,
            "repeatable": x.repeatable,
            "character_id": x.character_id,
            "probe_id": x.probe_id,
            "choice": x.choice,
            "parameters": x.parameters,
            "kdma_association": x.kdma_association,
            "action_conditions": json.loads(str(x.action_conditions).replace("'", '"').replace("None", '"None"')),
            "action_condition_semantics": x.action_condition_semantics,
            "probe_conditions": json.loads(str(x.probe_conditions).replace("'", '"').replace("None", '"None"')),
            "probe_condition_semantics": x.probe_condition_semantics,
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
            state_copy = copy.deepcopy(vars(self.state))
            del state_copy['openapi_types']
            del state_copy['attribute_map']
            state_copy = str(state_copy).encode('utf-8').decode('unicode-escape').replace('"', "'")
        to_obj = {
            "id": self.id,
            "state": state_copy,
            "end_scene_allowed": self.end_scene_allowed,
            "default_next_scene": self.default_next_scene,
            "persist_characters": self.persist_characters,
            "removed_characters": self.removed_characters,
            "actions_taken": self.actions_taken,
            "action_mappings": action_mappings,
            "restricted_actions": self.restricted_actions,
            "parent_scenario": self.parent_scenario.id,
            "training": self.training,
            "transition_semantics": self.transition_semantics,
            "transitions": json.loads(str(self.transitions).replace('"', '').replace("'", '"').replace("None", '"None"').replace("False", "false").replace("True", "true"))
        }
        return json.dumps(to_obj, indent=4)


    def __expose_action(self, mapping: ActionMapping, session_state: State):
        if not mapping.action_id in self.actions_taken or mapping.repeatable:
            if self._conditions_met(mapping.action_conditions, session_state, mapping.action_condition_semantics):
                return True
        return False


    def get_available_actions(self, state: State) -> List[Action]:
        actions: List[Action] = [
            Action(
                action_id=mapping.action_id,
                action_type=mapping.action_type,
                unstructured=mapping.unstructured,
                character_id=mapping.character_id,
                intent_action=mapping.intent_action,
                threat_state=mapping.threat_state,
                parameters=mapping.parameters,
                kdma_association=mapping.kdma_association if self.training else None
            )
            for mapping in self.action_mappings if self.__expose_action(mapping, state)
        ]

        # When all actions are intent actions, don't add unmapped action types.
        if len(actions) > 0 and all(action.intent_action for action in actions):
            shuffle(actions)
            return actions

        # Add most unmapped action types that aren't explicitly restricted.
        valid_action_types = self.get_valid_action_types(state)
        configured_action_types = [action.action_type for action in actions]

        for action_type in valid_action_types:
            actions.append(Action(
                action_id=action_type.lower(),
                action_type=action_type,
                unstructured=action_type.replace('_', ' ')
            ))

        # Add "end scene" action if configured and not already added as an action mapping.
        if self.end_scene_allowed and ActionTypeEnum.END_SCENE not in configured_action_types:
            actions.append(Action(action_id="end_scene_action", action_type=ActionTypeEnum.END_SCENE, unstructured="End the scene"))

        # Let's not be TOO predictable
        shuffle(actions)
        return actions


    def get_valid_action_types(self, state: State):
        # Start with the list of all action types, and remove from there.
        valid_action_types = get_swagger_class_enum_values(ActionTypeEnum)
        valid_action_types.remove(ActionTypeEnum.END_SCENE)
        valid_action_types.remove(ActionTypeEnum.SEARCH) # This requires support in configuration, so don't add it.
        valid_action_types.remove(ActionTypeEnum.MESSAGE) # This must be pre-configured, so don't add it.
        # Only add MOVE_TO if there are unseen characters.
        if not any(character.unseen for character in state.characters):
            valid_action_types.remove(ActionTypeEnum.MOVE_TO)

        mapping_action_types = []
        for mapping in self.action_mappings:
            mapping_action_types.append(mapping.action_type)
        return \
            [action_type for action_type in valid_action_types if action_type not in mapping_action_types if action_type not in self.restricted_actions]


    def action_taken(self, action: Action, session_state: State):
        self.actions_taken.append(action.action_id)
        found_mapping = False
        next_scene_id = None
        # Training mode only, meta_info.probe_response will be set in respond_to_probe if necessary
        if self.parent_scenario.session.kdma_training:
            self.parent_scenario.session.state.meta_info.probe_response = None
        for mapping in self.action_mappings:
            if mapping.action_id == action.action_id:
                found_mapping = True
                next_scene_id = mapping.next_scene
                # Respond to probes if conditions are met.
                if self._conditions_met(mapping.probe_conditions, session_state, mapping.probe_condition_semantics):
                    self.parent_scenario.respond_to_probe(mapping.probe_id, mapping.choice, action.justification)
                break  # action_id's are unique within a scene

        if not found_mapping: # Handle ADMs ordering something not on the menu
            next_scene_id = self.default_next_scene

        # Determine if we should transition to the next scene.
        if action.action_type == ActionTypeEnum.END_SCENE or \
            self._conditions_met(self.transitions, session_state, self.transition_semantics):
                self.parent_scenario.change_scene(next_scene_id)

    def _probe_condition_met(self, probe_conditions: List[str]) -> bool:
        if not probe_conditions:
            return True
        return all(probe in self.parent_scenario.probes_sent for probe in probe_conditions)

    def _probe_response_condition_met(self, probe_response_conditions: List[str]) -> bool:
        if not probe_response_conditions:
            return True
        return all(probe in self.parent_scenario.probe_responses_sent for probe in probe_response_conditions)

    def _elapsed_gt_condition_met(self, elapsed_gt, session_state: State) -> bool:
        if elapsed_gt is None:
            return True
        return session_state.elapsed_time > elapsed_gt

    def _elapsed_lt_condition_met(self, elapsed_lt, session_state: State) -> bool:
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
    def _evaluate_condition(self, property, eval_function, semantics, session_state=None):
        if property is not None and property != []:
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


    def evaluate_domain_conditions(self, conditions: Conditions, semantics, session_state: State):
        return False, semantics == SemanticTypeEnum.AND


    def _conditions_met(self, conditions: Conditions, session_state: State, semantics) -> bool:
        if not conditions:
            return True
        (short_circuit, probe_condition_met) = \
             self._evaluate_condition(conditions.probes, self._probe_condition_met, semantics)
        if short_circuit:
            return probe_condition_met
        (short_circuit, probe_response_condition_met) = \
             self._evaluate_condition(conditions.probe_responses, self._probe_response_condition_met, semantics)
        if short_circuit:
            return probe_response_condition_met
        (short_circuit, elapsed_gt_condition_met) = \
             self._evaluate_condition(conditions.elapsed_time_gt, self._elapsed_gt_condition_met, semantics, session_state)
        if short_circuit:
            return elapsed_gt_condition_met
        (short_circuit, elapsed_lt_condition_met) = \
             self._evaluate_condition(conditions.elapsed_time_lt, self._elapsed_lt_condition_met, semantics, session_state)
        if short_circuit:
            return elapsed_lt_condition_met
        (short_circuit, actions_condition_met) = \
             self._evaluate_condition(conditions.actions, self._actions_condition_met, semantics)
        if short_circuit:
            return actions_condition_met
        (short_circuit, domain_conditions_met) = \
            self.evaluate_domain_conditions(conditions, semantics, session_state)
        if short_circuit:
            return domain_conditions_met

        if (semantics == SemanticTypeEnum.AND):
            return True # if we didn't short-circuit, then all supplied conditions are True
        elif (semantics == SemanticTypeEnum.OR):
            return False # if we didn't short-circuit, then all supplied conditions are False
        else: # "not" semantics means that the overall condition is true if all of the conditions are false
            return True # if we didn't short-circuit, then all supplied conditions are False, so return True
