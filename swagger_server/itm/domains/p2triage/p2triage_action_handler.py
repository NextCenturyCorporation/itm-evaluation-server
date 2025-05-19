import json
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    Character
)
from swagger_server.itm import ITMActionHandler

class P2TriageActionHandler(ITMActionHandler):
    """
    Class for validating and processing p2triage actions.
    """
    def __init__(self, session):
        """
        Initialize a P2TriageActionHandler.
        """
        super().__init__(session)

    def load_action_times(self):
        super().load_action_times()
        # Add p2triage-specific action times
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

        if action.action_type == ActionTypeEnum.TREAT_PATIENT:
            # Character required
            if not action.action_id:
                return False, f'Malformed Action: Missing character_id for {action.action_type}', 400
            if character.unseen and not action.intent_action and action.action_type:
                return False, f'Cannot perform {action.action_type} action with unseen character `{action.character_id}`', 400
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        return True, '', 0


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
            case _: # Nothing to process except the passage of time
                time_passed = self.times_dict[action.action_type]

        return time_passed
