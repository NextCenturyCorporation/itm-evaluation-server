import json
import logging
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    Character
)
from .itm_scenario import ITMScenario
from .itm_scene import ITMScene

class ITMActionHandler:
    """
    Class for validating and processing actions.
    """

    def __init__(self, session):
        """
        Initialize an ITMActionHandler.
        """
        from.itm_session import ITMSession
        self.session: ITMSession = session
        self.current_scene: ITMScene = None
        self.times_dict: dict = None
        self.load_action_times()

    def load_action_times(self):
        with open("swagger_server/itm/data/actionTimes.json", 'r') as json_file:
                self.times_dict = json.load(json_file)
        json_file.close()

    def set_scene(self, scene):
        self.current_scene = scene

    def set_scenario(self, scenario: ITMScenario):
        self.current_scene = scenario.isd.current_scene


    def validate_domain_action(self, action: Action, character: Character):
        return True, '', 0


    def validate_action(self, action: Action):
        """
        Validate that action is a valid, well-formed action.

        Args:
            action: The action to validate.
        """

        if action is None:
            return False, 'Invalid or Malformed Action', 400

        if not action.action_type:
            return False, 'Invalid or Malformed Action: Missing action_type', 400

        if not action.justification:
            return False, 'Invalid or Malformed Action: Missing justification', 400

        if action.parameters and not isinstance(action.parameters, dict):
            return False, 'Malformed Action: Invalid Parameter Structure', 400

        if action.action_type in self.current_scene.restricted_actions or \
            action.action_type == ActionTypeEnum.END_SCENE and not self.current_scene.end_scene_allowed:
            return False, 'Invalid Action: action restricted', 400

        # Validate specified character exists
        character = None
        if action.character_id:
            character = next((character for character in self.session.state.characters if character.id == action.character_id), None)
            if not character:
                return False, f'Character `{action.character_id}` not found in state', 400

        # type checks for possible fields
        if action.unstructured and not isinstance(action.unstructured, str):
            return False, 'Malformed Action: Invalid unstructured description', 400

        if action.justification and not isinstance(action.justification, str):
            return False, 'Malformed Action: Invalid justification', 400

        # Validate specific actions
        if action.action_type == ActionTypeEnum.MESSAGE:
            # Ensure they chose one of the pre-configured actions and didn't make up their own MESSAGE
            scene_action_ids = [mapping.action_id for mapping in self.current_scene.action_mappings]
            if action.action_id not in scene_action_ids:
                return False, f'Malformed {action.action_type} Action: action_id `{action.action_id}` is not a valid action_id from the current scene', 400
        elif action.action_type == ActionTypeEnum.MOVE_TO:
            # Character is required
            if not character:
                return False, f'Malformed Action: Missing character_id for {action.action_type}', 400
            # Can only target unseen characters
            if not character.unseen:
                return False, f'Can only {action.action_type} an "unseen" character, but `{action.character_id}` is "seen".', 400
        elif action.action_type in [ActionTypeEnum.END_SCENE, ActionTypeEnum.SEARCH]:
            return True, '', 0 # Requires nothing
        else: # Passed base validation; validate domain-level actions
            return self.validate_domain_action(action, character)

        return True, '', 0


    def move_to(self, target_character: Character):
        """
        Move to the location of the specified character, toggling whether all characters are seen or not.
        NOTE: This only works when there are only two locations, which is the stated requirement.

        Args:
            target_character: The character to move to
        """

        # NOTE: With the current two-room-only implementation, the target_character isn't actually used in the code.
        # If we ever implement multiple locations, we'll need to know which character the ADM is moving to.
        for character in self.session.state.characters:
            character.unseen = not character.unseen
        return self.times_dict[ActionTypeEnum.MOVE_TO]


    def search(self):
        """
        Search for more characters.
        """
        # After a search, the ADM is at a new location (which may or may not have patients), so all previous characters become unseen.
        for character in self.session.state.characters:
            character.unseen = True
        return self.times_dict[ActionTypeEnum.SEARCH]


    def process_domain_action(self, action: Action, character: Character, parameters: dict) -> int:
        pass


    def process_action(self, action: Action):
        """
        Process the taken action, including tracking elapsed time and telling the scene
        which action was taken. The action should be fully validated via `validate_action()`.

        Args:
            action: The action to process.
        """
        # keeps track of time passed based on action taken (in seconds)
        time_passed = 0
        # Look up character action is applied to
        character = next((character for character in self.session.state.characters \
                         if character.id == action.character_id), None)

        parameters = {"action_type": action.action_type, "action_id": action.action_id,
                      "justification": action.justification, "session_id": self.session.session_id}
        if character:
            parameters['character'] = action.character_id
        match action.action_type:
            case ActionTypeEnum.MOVE_TO:
                time_passed = self.move_to(character)
            case ActionTypeEnum.SEARCH:
                time_passed = self.search()
            case ActionTypeEnum.MESSAGE | ActionTypeEnum.END_SCENE:
                time_passed = self.times_dict[action.action_type]
            case _: # Nothing to process except the passage of time
                time_passed = self.process_domain_action(action, character, parameters)

        self.session.state.elapsed_time += time_passed
        # Log the action
        self.session.history.add_history("Take Action", parameters,
                                         self.session.state.to_dict())

        # Tell Scene what happened
        self.current_scene.action_taken(action=action, session_state=self.session.state)


    # Collect base parameters for the intended action for logging purposes
    def add_intent_parameters(self, action: Action, parameters: dict):
        # Look up character action is applied to
        character = next((character for character in self.session.state.characters \
                         if character.id == action.character_id), None)
        if character:
            parameters['character'] = action.character_id
        parameters['action_type'] = action.action_type
        parameters['action_id'] = action.action_id
        parameters['justification'] = action.justification
        parameters['session_id'] = self.session.session_id


    def process_intention(self, action: Action):
        """
        Process the intended action including telling the scene which action was taken.
        The action should be fully validated via `validate_action()`.

        Args:
            action: The action to process.
        """

        parameters = {}
        # Add intent parameters
        self.add_intent_parameters(action, parameters)

        # Log the intention
        self.session.history.add_history("Intend Action", parameters,
                                         self.session.state.to_dict())

        # Tell Scene what happened
        self.current_scene.action_taken(action=action, session_state=self.session.state)
