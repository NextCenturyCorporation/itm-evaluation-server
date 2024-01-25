from dataclasses import dataclass
from typing import List, Dict
from swagger_server.models.scene import Scene
from swagger_server.models.action import Action
from swagger_server.models.action_type_enum import ActionTypeEnum
from swagger_server.models.conditions import Conditions
from swagger_server.models.semantic_type_enum import SemanticTypeEnum
from swagger_server.models.state import State

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
        self.next_scene = scene_index+1 if action.next_scene == None else action.next_scene

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
        self.action_mappings :List[ActionMapping] = [
            ActionMapping(action_mapping, self.index)
            for action_mapping in scene.action_mapping
        ]
        self.restricted_actions :List[ActionTypeEnum] = scene.restricted_actions
        self.transition_semantics :SemanticTypeEnum = scene.transition_semantics
        self.transitions :Conditions = scene.transitions
