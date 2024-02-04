import copy
import json
from typing import List, Dict
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
        self.state :State = scene.state
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
        actions :List[ActionMapping] = [
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

    def action_taken(self, action_id: str, justification: str):
        for mapping in self.action_mappings:
            if mapping.action_id == action_id:
                self.actions_taken.append(mapping.action_id)
                # Respond to probes if conditions are met.
                if ITMScene.conditions_met(mapping.conditions):
                    self.parent_scenario.respond_to_probe(mapping.probe_id, mapping.choice, justification)
                # Determine if we should transition to the next scene.
                if ITMScene.conditions_met(self.transitions, self.transition_semantics):
                    self.parent_scenario.change_scene(mapping.next_scene)

    # TODO: implement based on configured conditions
    @staticmethod
    def conditions_met(conditions :Conditions, semantics="and") -> bool:
        return conditions # for now, return True if there are any conditions, otherwise False