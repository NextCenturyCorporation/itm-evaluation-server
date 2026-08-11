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
    TAG_TEXT = ' They are currently tagged ' # Added to unstructured text when tagged

    def __init__(self, session):
        """
        Initialize a OWTriageActionHandler.
        """
        super().__init__(session)
        self.shadow_characters: dict = None # Copies of the characters where obscured info isn't scrubbed
        self.shadow: Character = None # The shadow character of the current action

    def load_action_times(self):
        super().load_action_times()
        # Add owtriage-specific action times
        filespec = self.session.domain_config.get_action_time_filespec()
        with open(filespec, 'r') as json_file:
            self.times_dict.update(json.load(json_file))
        json_file.close()

    def move_only_to_unseen(self) -> bool:
        return False


    def set_scenario(self, scenario):
        super().set_scenario(scenario)
        self.shadow_characters = {char.id: deepcopy(char) for char in self.session.state.characters} # One-time initialization


    def set_scene(self, scene):
        super().set_scene(scene)
        # Add shadow for new characters
        # NOTE: updating or removing a character via YAML is not currently supported; only adding one
        for isd_character in self.current_scene.state.characters:
            if isd_character.id not in self.shadow_characters:
                logging.info(f"{self.session.log_id}: Adding new character {isd_character.id} to shadow.")
                self.shadow_characters[isd_character.id] = deepcopy(isd_character)


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
            if self.shadow_characters:
                if character.id in self.shadow_characters:
                    self.shadow = self.shadow_characters[character.id]
                else:
                    return False, f'Invalid character id `{character.id}`', 400

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


    # We assume that `character` and its shadow has been updated based on the current action
    def update_one_unstructured(self, character: Character):
        char_id = character.id
        shadow: Character = self.shadow_characters[char_id]

        # Determine the attribute suffix based on character states
        treated_suffix = "_treated" if shadow.treated else ""
        distance_suffix = "_near" if character.nearby else "_far"

        # Dynamically fetch the correct unstructured text from shadow
        attr_name = f"unstructured{treated_suffix}{distance_suffix}"
        base_text = getattr(shadow, attr_name)

        # Apply optional tag text
        if shadow.tag and shadow.nearby:
            base_text += self.TAG_TEXT + shadow.tag + '.'

        # Assign the final string to both objects
        character.unstructured = shadow.unstructured = base_text if base_text else 'Unknown'


    # We assume that the shadow has been updated based on the current action along with all characters
    def update_unstructured(self, one_character=None):
        if one_character:
            self.update_one_unstructured(one_character)
        else:
            for character in self.session.state.characters:
                self.update_one_unstructured(character)


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
        self.shadow_characters[character.id].treated = True
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
        # Update visibility and nearness
        target_distance = self.shadow_characters[target_character.id].distance
        is_target_unseen = target_character.unseen
        logging.info(f"{self.session.log_id}: Moving to {'unseen' if target_character.unseen else 'seen'} character {target_character.name}.")

        for character in self.session.state.characters:
            if is_target_unseen:
                # Invert the unseen status for all characters
                character.unseen = not character.unseen
                # If they are now visible, check proximity to target, otherwise they are distant
                character.nearby = (not character.unseen) and (self.shadow_characters[character.id].distance == target_distance)
            elif not character.unseen:
                # Only update already seen characters
                character.nearby = self.shadow_characters[character.id].distance == target_distance

        # Update shadows and restore tag of nearby characters
        for char in self.session.state.characters:
            self.shadow_characters[char.id].unseen = char.unseen
            self.shadow_characters[char.id].nearby = char.nearby
            if char.nearby:
                char.tag = self.shadow_characters[char.id].tag
        # Update description of all characters
        self.update_unstructured()

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
                self.shadow.vitals = deepcopy(isd_character.vitals)
                return self.times_dict[ActionTypeEnum.CHECK_VITALS]


    def move_to_evac(self, character: Character):
        """
        Move the specified character to the evacuation zone (or equivalent), removing the character from the state.

        Args:
            character: The character to move to evac.
        """
        self.session.state.characters = [char for char in self.session.state.characters if char.id != character.id]
        self.shadow_characters.pop(character.id, None)
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
        character.unstructured = character.unstructured.split(self.TAG_TEXT)[0] + self.TAG_TEXT + tag + '.'
        self.shadow.tag = tag
        self.shadow.unstructured = character.unstructured
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
