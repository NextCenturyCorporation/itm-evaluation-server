import json
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    Character
)
from swagger_server.itm import ITMActionHandler

class WumpusActionHandler(ITMActionHandler):
    """
    Class for validating and processing wumpus actions.
    """
    def __init__(self, session):
        """
        Initialize a WumpusActionHandler.
        """
        super().__init__(session)

    def load_action_times(self):
        super().load_action_times()
        # Add wumpus-specific action times
        filespec = self.session.domain_config.get_action_time_filespec()
        with open(filespec, 'r') as json_file:
            self.times_dict.update(json.load(json_file))
        json_file.close()


    def validate_domain_action(self, action: Action, character: Character):
        """
        Validate that action is a valid, well-formed action.
        The action has already passed base level validation.

        Args:
            action: The action to validate.
            character: The character specified in the action, if any
        """

        if action.action_type == ActionTypeEnum.SHOOT:
            pass # Place-holder
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        return True, '', 0


    def shoot(self, character: Character, parameters: dict):
        """
        Shoot (placeholder)

        Args:
            character: The character
        """
        return self.times_dict[ActionTypeEnum.SHOOT]


    def process_domain_action(self, action: Action, character: Character, parameters: dict) -> int:
        """
        Process the taken domain-specific action, returning elapsed time.
        The action should be fully validated via `validate_action()`

        Args:
            action: The action to process
            character: The character (if any) upon whom the action was taken
            parameters: action-specific parameters
        """
        match action.action_type:
            case ActionTypeEnum.SHOOT:
                time_passed = self.shoot(character, parameters)
            case _: # Nothing to process except the passage of time
                time_passed = self.times_dict[action.action_type]

        return time_passed
