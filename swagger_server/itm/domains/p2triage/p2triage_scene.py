from swagger_server.models import (
    ActionTypeEnum, Scene, State
)
from swagger_server.itm import ITMScene

class P2TriageScene(ITMScene):
    """
    Class for managing a p2triage scene in the ITM system.
    """

    def __init__(self, scene: Scene):
        """
        Initialize an instance of P2TriageScene.
        """
        super().__init__(scene)

    def get_valid_action_types(self, state: State):
        return [] # Don't add actions in this domain
