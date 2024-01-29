import copy
import json
from dataclasses import dataclass
from typing import List, Dict
from swagger_server.models import (
    Scene, Action, ActionTypeEnum, Conditions, SemanticTypeEnum, State, ProbeResponse
)

@dataclass
class ActionMapping:
    """Class to represent a mapping from action to probe response."""
    action_id: str
    action_type: str
    unstructured: str
    character_id: str
    probe_id: str
    choice: str
    kdma_association :Dict[str, float]
    conditions :Conditions
    next_scene :int

    def __init__(self, action :Action, scene_index :int):
        self.action_id = action.action_id
        self.action_type = action.action_type
        self.unstructured = action.unstructured
        self.character_id = action.character_id
        self.probe_id = action.probe_id
        self.choice = action.choice
        self.kdma_association = action.kdma_association
        self.conditions = action.conditions
        self.next_scene = scene_index+1 if action.next_scene is None else action.next_scene

    def to_obj(self):
        '''
        Override method to pretty-print action mapping
        '''
        to_obj = {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "unstructured": self.unstructured,
            "character_id": self.character_id,
            "probe_id": self.probe_id,
            "choice": self.choice,
            "kdma_association": self.kdma_association,
            "conditions": json.loads(str(self.conditions).replace("'", '"').replace("None", '"None"')),
            "next_scene": self.next_scene
        }
        return to_obj

class ITMScene:
    """
    Class for managing a scene in the ITM system.
    """

    def __init__(self, scene :Scene):
        """
        Initialize an instance of ITMScene.
        """
        self.index :int = scene.index
        self.state :State = scene.state
        self.end_scene_allowed :bool = scene.end_scene_allowed
        self.action_mappings :List[ActionMapping] = [
            ActionMapping(action_mapping, self.index)
            for action_mapping in scene.action_mapping
        ]
        self.restricted_actions :List[ActionTypeEnum] = scene.restricted_actions
        self.transition_semantics :SemanticTypeEnum = scene.transition_semantics
        self.transitions :Conditions = scene.transitions

    def __str__(self):
        '''
        Override method to pretty-print itm scene
        '''
        action_mappings = []
        for x in self.action_mappings:
            action_mappings.append(x.to_obj())
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

    # TODO: Return action_mapping actions + unmapped actions - restricted actions
    def get_available_actions(self) -> List[Action]:
        actions: List[Action] = []
        if self.end_scene_allowed:
            actions.append(Action(action_id="end_scene_action", action_type='END_SCENE', unstructured="End the scene"))

        return actions

    def lookup_probe_response(self, action_id) -> ProbeResponse:
        return ProbeResponse(scenario_id=self.scenario.id, probe_id=currentProbe.id,
                             choice=choice_id, justification=action.justification) if choice_id != None else None
