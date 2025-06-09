from swagger_server.models import (
    Conditions, Scene, SemanticTypeEnum, State
)
from swagger_server.itm import ITMScene

class WumpusScene(ITMScene):
    """
    Class for managing a wumpus scene in the ITM system.
    """

    def __init__(self, scene: Scene):
        """
        Initialize an instance of WumpusScene.
        """
        super().__init__(scene)

    def get_valid_action_types(self, state: State):
        remaining_action_types = super().get_valid_action_types(state)
        return remaining_action_types


    def _foobar_condition_met(self, foobar_conditions: str, session_state: State) -> bool:
        if not foobar_conditions:
            return True
        foobar_conditions_met = True
        return foobar_conditions_met


    def evaluate_domain_conditions(self, conditions: Conditions, semantics, session_state: State):
        (short_circuit, foobar_condition_met) = \
             self._evaluate_condition(conditions.foobar, self._foobar_condition_met, semantics, session_state)
        if short_circuit:
            return True, foobar_condition_met

        return False, semantics == SemanticTypeEnum.AND

