from dataclasses import dataclass
from typing import List, Dict
from swagger_server.models.scene import Scene


 
class ITMScene:
    """
    Class for managing a scene in the ITM system.
    """

    def __init__(self, scene :Scene):
        """
        Initialize an instance of ITMScene.
        """
        self.scene :Scene = scene
