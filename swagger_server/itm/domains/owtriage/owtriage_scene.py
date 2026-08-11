from swagger_server.models import (
    Scene, State
)
from swagger_server.itm import ITMScene

class OWTriageScene(ITMScene):
    """
    Class for managing a owtriage scene in the ITM system.
    """

    def __init__(self, scene: Scene):
        """
        Initialize an instance of OWTriageScene.
        """
        super().__init__(scene)

    def get_valid_action_types(self, state: State):
        return [] # Don't add actions in this domain
