import json
import logging
from copy import deepcopy
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    CharacterTagEnum,
    Character
)
from swagger_server.itm import ITMActionHandler
from swagger_server.util import get_swagger_class_enum_values

class OWTriageActionHandler(ITMActionHandler):
    """
    Class for validating and processing owtriage actions.
    """
    TAG_TEXT = '. They are currently tagged ' # Added to unstructured text when tagged

    def __init__(self, session):
        """
        Initialize a OWTriageActionHandler.
        """
        super().__init__(session)

    def load_action_times(self):
        super().load_action_times()
        # Add owtriage-specific action times
        filespec = self.session.domain_config.get_action_time_filespec()
        with open(filespec, 'r') as json_file:
            self.times_dict.update(json.load(json_file))
        json_file.close()

    def move_only_to_unseen(self) -> bool:
        return False


    def validate_domain_action(self, action: Action, character: Character):
        """
        Validate that action is a valid, well-formed action.
        The action has already passed base level validation.

        Args:
            action: The action to validate.
            character: The character specified in the action, if any
        """

        if action.action_type in [ActionTypeEnum.TREAT_PATIENT, ActionTypeEnum.CHECK_VITALS, ActionTypeEnum.TAG_CHARACTER, ActionTypeEnum.MOVE_TO_EVAC]:
            # Character required
            if not character or not character.id:
                return False, f'Malformed Action: Missing character_id for {action.action_type}', 400
            if action.action_type != ActionTypeEnum.MOVE_TO_EVAC and not action.intent_action:
                if character.unseen:
                    return False, f'Cannot perform {action.action_type} action with unseen character `{action.character_id}`', 400
                if not character.nearby:
                    return False, f'Cannot perform {action.action_type} action with a distant character `{action.character_id}`', 400

        if action.action_type == ActionTypeEnum.TAG_CHARACTER:
            # Requires category parameter
            if not action.parameters or not 'category' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `category` parameter', 400
            else:
                allowed_values = get_swagger_class_enum_values(CharacterTagEnum)
                tag = action.parameters.get('category')
                if not tag in allowed_values:
                    return False, f'Malformed {action.action_type} Action: Invalid Tag `{tag}`', 400
        elif action.action_type == ActionTypeEnum.TREAT_PATIENT:
            # Ensure there are sufficient Supplies for the treatment. This check also catches invalid treatment values.
            supply_used = action.parameters.get('treatment', None)
            sufficient_supplies = False
            for supply in self.session.state.supplies:
                if supply.type == supply_used:
                    sufficient_supplies = supply.quantity >= 1
                    break
            if not sufficient_supplies:
                return False, f'Invalid or insufficient `{supply_used}` supplies', 400
        elif action.action_type in [ActionTypeEnum.CHECK_VITALS, ActionTypeEnum.MOVE_TO_EVAC]:
            pass # Requires nothing further
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        return True, '', 0


    def update_unstructured(self, one_character=None):
        if one_character:
            pass
        for character in self.session.state.characters:
            for isd_character in self.current_scene.state.characters:
                if isd_character.id == character.id:
                    tag_index = character.unstructured.find(self.TAG_TEXT)
                    tag_text = character.unstructured[tag_index:]
                    if character.nearby:
                        character.unstructured = isd_character.unstructured_treated_near if character.treated else isd_character.unstructured_near
                        if tag_index > 0: # tagged
                            character.unstructured += tag_text
                    else:
                        character.unstructured = isd_character.unstructured_treated_far if character.treated else isd_character.unstructured_treated_far


    def treat_patient(self, character: Character, supply_used: str):
        """
        Apply a treatment to the specified character.

        Args:
            character: The character to treat
            supply_used: The supply (treatment) to use on the character
        """

        # Ignore re-treating a character
        if character.treated:
            return 0

        character.treated = True
        self.update_unstructured(character)

        for supply in self.session.state.supplies:
            if supply.type == supply_used:
                if supply.quantity:
                    supply.quantity -= 1
                    logging.info("%s: Decrementing %s to %d", self.session.log_id, supply.type, supply.quantity)

        return self.times_dict[ActionTypeEnum.TREAT_PATIENT]


    # Override base class implementation
    def move_to(self, target_character: Character):
        """
        Move to the location of the specified character, whether near, distant, or unseen.

        Args:
            target_character: The character to move to
        """
        # TODO/TBDDAG: Refactor this; it could be simplified
        # Update visibility and nearness
        target_distance = target_character.distance
        logging.info(f"Moving to {'unseen' if target_character.unseen else 'seen'} character {target_character.name}.")
        if target_character.unseen:
            for character in self.session.state.characters:
                if character.unseen:
                    character.unseen = False
                    character.nearby = character.distance == target_distance
                else:
                    character.unseen = True
                    character.nearby = False
        else:
            for character in self.session.state.characters:
                if not character.unseen:
                    character.nearby = character.distance == target_distance
                    logging.info(f"--> Seen character {character.id}.nearby is now {character.nearby}.")

        # Update description
        self.update_unstructured(self)

        return self.times_dict[ActionTypeEnum.MOVE_TO]


    def check_vitals(self, character: Character):
        """
        Check vitals of the specified character in the scenario.

        Args:
            character: The character to check.
        """
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                character.vitals = deepcopy(isd_character.vitals)
                return self.times_dict[ActionTypeEnum.CHECK_VITALS]


    def move_to_evac(self, character: Character):
        """
        Move the specified character to the evacuation zone (or equivalent), removing the character from the state.

        Args:
            character: The character to move to evac.
        """
        self.session.state.characters = [char for char in self.session.state.characters if char.id != character.id]
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
                time_passed = self.treat_patient(character, action.parameters['treatment'])
                parameters['treatment'] = action.parameters['treatment']
            case ActionTypeEnum.CHECK_VITALS:
                time_passed = self.check_vitals(character)
            case ActionTypeEnum.MOVE_TO_EVAC:
                time_passed = self.move_to_evac(character)
            case ActionTypeEnum.TAG_CHARACTER:
                # The tag is specified in the category parameter
                time_passed = self.tag_character(character, action.parameters['category'])
                parameters['category'] = action.parameters['category']
            case _: # Nothing to process except the passage of time
                time_passed = self.times_dict[action.action_type]

        return time_passed
