import json
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    CharacterTagEnum,
    Character
)
from swagger_server.itm import ITMActionHandler
from swagger_server.util import get_swagger_class_enum_values

class P2TriageActionHandler(ITMActionHandler):
    """
    Class for validating and processing p2triage actions.
    """
    TAG_TEXT = '. They are currently tagged ' # Added to unstructured text when tagged

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

        if action.action_type in [ActionTypeEnum.TREAT_PATIENT, ActionTypeEnum.TAG_CHARACTER, ActionTypeEnum.MOVE_TO_EVAC]:
            # Character required
            if not character or not character.id:
                return False, f'Malformed Action: Missing character_id for {action.action_type}', 400
            if character.unseen and not action.intent_action:
                return False, f'Cannot perform {action.action_type} action with unseen character `{action.character_id}`', 400

        if action.action_type == ActionTypeEnum.TAG_CHARACTER:
            # Requires category parameter
            if not action.parameters or not 'category' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `category` parameter', 400
            else:
                allowed_values = get_swagger_class_enum_values(CharacterTagEnum)
                tag = action.parameters.get('category')
                if not tag in allowed_values:
                    return False, f'Malformed {action.action_type} Action: Invalid Tag `{tag}`', 400
        elif action.action_type in [ActionTypeEnum.TREAT_PATIENT, ActionTypeEnum.MOVE_TO_EVAC]:
            pass # Requires nothing
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        return True, '', 0


    def treat_patient(self, character: Character):
        """
        Apply a treatment to the specified character.

        Args:
            character: The character to treat
        """

        # Update unstructured text to reflect treatment; strip out patient true name first; preserve tag.
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                if isd_character.unstructured_posttreatment:
                    tag_index = character.unstructured.find(self.TAG_TEXT)
                    if tag_index > 0: # tagged
                        character.unstructured = isd_character.unstructured_posttreatment.split(';')[0] + \
                            character.unstructured[tag_index:]
                    else: # untagged
                        character.unstructured = isd_character.unstructured_posttreatment.split(';')[0]
        return self.times_dict[ActionTypeEnum.TREAT_PATIENT]


    def move_to_evac(self, character: Character):
        """
        Move the specified character to the evacuation zone (or equivalent).

        Args:
            character: The character to move to evac
        """
        character.unseen = True
        # Update unstructured text to reflect evacuation.
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                character.unstructured += '. This patient has been moved to the evacuation zone.'
        return self.times_dict[ActionTypeEnum.MOVE_TO_EVAC]


    def tag_character(self, character: Character, tag: str):
        """
        Tag the specified character with a triage category

        Args:
            character: The character to tag
            tag: The tag to assign to the character. Replaces old tag if present.
        """
        character.tag = tag
        # Update unstructured text to reflect tagging; support re-tagging.
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                character.unstructured = \
                    character.unstructured.split(self.TAG_TEXT)[0] + self.TAG_TEXT + tag + '.'
                return self.times_dict[ActionTypeEnum.TAG_CHARACTER]


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
            case ActionTypeEnum.TREAT_PATIENT:
                time_passed = self.treat_patient(character)
            case ActionTypeEnum.MOVE_TO_EVAC:
                time_passed = self.move_to_evac(character)
            case ActionTypeEnum.TAG_CHARACTER:
                # The tag is specified in the category parameter
                time_passed = self.tag_character(character, action.parameters.get('category'))
                parameters['category'] = action.parameters['category']
            case _: # Nothing to process except the passage of time
                time_passed = self.times_dict[action.action_type]

        return time_passed
