import json
from swagger_server.models import (
    Action,
    Character
)
from swagger_server.models.action_type import ActionType
from swagger_server.models.character_tag import CharacterTag
from swagger_server.models.injury_location import InjuryLocation
from swagger_server.util import get_swagger_class_enum_values
from .itm_session_scenario_object import ITMSessionScenarioObject

class ITMActionHandler:
    """
    Class for validating and processing actions.
    """

    def __init__(self, session):
        """
        Initialize an ITMActionHandler.
        """
        from.itm_scenario_session import ITMScenarioSession
        self.session: ITMScenarioSession = session
        self.current_isso: ITMSessionScenarioObject = None
        with open("swagger_server/itm/treatment_times_config/actionTimes.json", 'r') as json_file:
                self.times_dict = json.load(json_file)

    def set_isso(self, isso):
        self.current_isso = isso

    def _should_reveal_injury(self, source_injury, target):
        return source_injury.name in self.current_isso.hidden_injury_types and \
               not any(target_injury.name in self.current_isso.hidden_injury_types for target_injury in target.injuries)

    def _reveal_injuries(self, source: Character, target: Character):
        if target.visited: # Don't reveal injuries in visited characters
            return

        revealed_injuries = [source_injury for source_injury in source.injuries if self._should_reveal_injury(source_injury, target)]
        target.injuries.extend(revealed_injuries)

        # TODO: develop a system for scenarios to specify changes in plaintext Character description
        if self.session.scenario_rules == "SOARTECH":
            if target.id == 'MarineA':
                target.unstructured += \
                    "Burns of overall extremities and the majority of the torso and face, " + \
                    "with peppered dirt and shrapnel on all extremities (BSA covers 90% of his body)."
            elif target.id == 'Intelligence Officer':
                target.unstructured += \
                    "Initial injuries show 2nd and 3rd degree burns of the left half of his body (BSA is 50%) " + \
                    "with peppered dirt and shrapnel over the same area."


    def _proper_treatment(self, treatment: str, injury_name: str, location: str) -> bool:
        # NOTE: Asthmatic, Burns, Forehead Scrape, Ear Bleed are currently untreatable
        # This logic is in sync with the current OSU Simulator, but may diverge at a later date.
        """
            Head Injuries
            Forehead Scrape: None
            Face Shrapnel: Nasopharyngeal airway
            Ear Bleed: None

            Neck Injuries
            Neck Puncture: Hemostatic gauze

            Hand Injuries
            Wrist Amputation: Tourniquet
            Palm Laceration: Pressure bandage

            Arm Injuries
            Forearm Laceration: Pressure bandage
            Bicep Puncture: Tourniquet
            Shoulder Puncture: Hemostatic gauze

            Chest Injuries
            Asthmatic: None
            Chest Collapse: Decompression Needle

            Stomach Injuries
            Stomach Laceration: Pressure bandage
            Stomach Puncture: Hemostatic gauze
            Side Puncture: Hemostatic gauze

            Leg Injuries
            Thigh Puncture: Tourniquet
            Thigh Laceration: Tourniquet
            Shin Amputation: Tourniquet
            Calf Laceration: Pressure bandage
            Calf Shrapnel: Hemostatic gauze
        """
        match injury_name:
            case 'Amputation':
                return treatment == 'Tourniquet'
            case 'Chest Collapse':
                return treatment == 'Decompression Needle'
            case 'Laceration':
                if 'thigh' in location:
                    return treatment == 'Tourniquet'
                else:
                    return treatment == 'Pressure bandage'
            case 'Puncture':
                if 'bicep' in location or 'thigh' in location:
                    return treatment == 'Tourniquet'
                else:
                    return treatment == 'Hemostatic gauze'
            case 'Shrapnel':
                if 'face' in location:
                    return treatment == 'Nasopharyngeal airway'
                else:
                    return treatment == 'Hemostatic gauze'
            case _:
                return False


    def validate_action(self, action: Action) -> None:
        """
        Validate that action is a valid, well-formed action.

        Args:
            action: The action to validate.

        """

        if action is None:
            return False, 'Invalid or Malformed Action', 400

        if not action.action_type:
            return False, 'Invalid or Malformed Action: Missing action_type', 400

        if action.parameters and not isinstance(action.parameters, dict):
            return False, 'Malformed Action: Invalid Parameter Structure', 400
        # lookup character id in state
        character = None
        if action.character_id:
            character = next((character for character in self.session.scenario.state.characters if character.id == action.character_id), None)

        # Validate character when necessary
        if (action.action_type in [ActionType.APPLY_TREATMENT, ActionType.CHECK_ALL_VITALS, ActionType.CHECK_PULSE, ActionType.CHECK_RESPIRATION, ActionType.MOVE_TO_EVAC, ActionType.TAG_CHARACTER]):
            if not action.character_id:
                return False, f'Malformed Action: Missing character_id for {action.action_type}', 400
            elif not character:
                return False, f'Character `{action.character_id}` not found in state', 400

        if action.action_type == ActionType.APPLY_TREATMENT:
            # Apply treatment requires a character id and parameters (treatment and location)
            # treatment and location
            valid_locations = get_swagger_class_enum_values(InjuryLocation)
            if not action.parameters or not 'treatment' in action.parameters or not 'location' in action.parameters:
                return False, f'Malformed Action: Missing parameters for {action.action_type}', 400
            elif 'location' in action.parameters and action.parameters['location'] not in valid_locations:
                return False, f"Malformed Action: Invalid location `{action.parameters['location']}` for {action.action_type}", 400
            # Ensure there are sufficient Supplies for the treatment. This check also catches invalid treatment values.
            supply_used = action.parameters.get('treatment', None)
            sufficient_supplies = False
            for supply in self.session.scenario.state.supplies:
                if supply.type == supply_used:
                    sufficient_supplies = supply.quantity >= 1
                    break
            if not sufficient_supplies:
                return False, f'Invalid or insufficient `{supply_used}` supplies', 400
        elif action.action_type == ActionType.SITREP:
            # sitrep optionally takes a character id
            if action.character_id and not character:
                return False, f'Character `{action.character_id}` not found in state', 400
        elif action.action_type == ActionType.TAG_CHARACTER:
            # Requires category parameter
            if not action.parameters or not 'category' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `category` parameter', 400
            else:
                allowed_values = get_swagger_class_enum_values(CharacterTag)
                tag = action.parameters.get('category')
                if not tag in allowed_values:
                    return False, f'Malformed {action.action_type} Action: Invalid Tag `{tag}`', 400
        elif action.action_type == ActionType.CHECK_ALL_VITALS or action.action_type == ActionType.CHECK_PULSE \
            or action.action_type == ActionType.CHECK_RESPIRATION or action.action_type == ActionType.MOVE_TO_EVAC:
            pass # Character was already checked
        elif action.action_type == ActionType.DIRECT_MOBILE_CHARACTERS or action.action_type == ActionType.END_SCENARIO:
            pass # Requires nothing
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        # type checks for possible fields
        if action.unstructured and not isinstance(action.unstructured, str):
            return False, 'Malformed Action: Invalid unstructured description', 400

        if action.justification and not isinstance(action.justification, str):
            return False, 'Malformed Action: Invalid justification', 400

        return True, '', 0


    def apply_treatment(self, action: Action, character: Character):
        """
        Apply a treatment to the specified character.

        Args:
            character: The character to treat
            action: The action which specifies parameters such as the treatment to apply and
            the location to treat.
        """
        # Remove injury from character if the treatment treats the injury at the specified location
        # NOTE: this assumes there is only one injury per location.
        supply_used = action.parameters.get('treatment', None)
        for injury in character.injuries:
            if injury.location == action.parameters.get('location', None):
                if self._proper_treatment(supply_used, injury.name, injury.location):
                    character.injuries.remove(injury)

        # Decrement supplies and increment time passed during treatment, even if the injury is untreated
        time_passed = 0
        for supply in self.session.scenario.state.supplies:
            if supply.type == supply_used:
                supply.quantity -= 1
                if supply_used in self.times_dict["treatmentTimes"]:
                    time_passed = self.times_dict["treatmentTimes"][supply_used]
                break

        # Injuries and certain basic vitals are discovered when a character is treated.
        for isso_character in self.current_isso.scenario.state.characters:
            if isso_character.id == character.id:
                character.vitals.breathing = isso_character.vitals.breathing
                character.vitals.conscious = isso_character.vitals.conscious
                character.vitals.mental_status = isso_character.vitals.mental_status
                self._reveal_injuries(isso_character, character)
                character.visited = True

        # Finally, return the elapsed time
        return time_passed


    def check_all_vitals(self, character: Character):
        """
        Check all vitals of the specified character in the scenario.

        Args:
            character: The character to check.
        """
        for isso_character in self.current_isso.scenario.state.characters:
            if isso_character.id == character.id:
                character.vitals = isso_character.vitals
                self._reveal_injuries(isso_character, character)
                character.visited = True
                return self.times_dict['CHECK_ALL_VITALS']


    def check_pulse(self, character: Character):
        """
        Process checking the pulse (heart rate) of the specified character.

        Args:
            character: The character to check.
        """
        for isso_character in self.current_isso.scenario.state.characters:
            if isso_character.id == character.id:
                character.vitals.breathing = isso_character.vitals.breathing
                character.vitals.conscious = isso_character.vitals.conscious
                character.vitals.mental_status = isso_character.vitals.mental_status
                character.vitals.hrpmin = isso_character.vitals.hrpmin
                self._reveal_injuries(isso_character, character)
                character.visited = True
                return self.times_dict['CHECK_PULSE']


    def check_respiration(self, character: Character):
        """
        Check the respiration of the specified character in the scenario.

        Args:
            character: The character to check.
        """
        for isso_character in self.current_isso.scenario.state.characters:
            if isso_character.id == character.id:
                character.vitals.breathing = isso_character.vitals.breathing
                character.vitals.conscious = isso_character.vitals.conscious
                character.vitals.mental_status = isso_character.vitals.mental_status
                self._reveal_injuries(isso_character, character)
                character.visited = True
                return self.times_dict['CHECK_RESPIRATION']


    def direct_mobile_characters(self):
        """
        Direct mobile characters to a safe zone (or equivalent).
        """
        return self.times_dict["DIRECT_MOBILE_CHARACTERS"]


    def move_to_evac(self, character: Character):
        """
        Move the specified character to the evacuation zone (or equivalent).

        Args:
            character: The character to move to evac
        """
        return self.times_dict["MOVE_TO_EVAC"]


    def tag_character(self, character: Character, tag: str):
        """
        Tag the specified character with a triage category

        Args:
            character: The character to tag
            tag: The tag to assign to the character.
        """
        character.tag = tag
        for isso_character in self.current_isso.scenario.state.characters:
            if isso_character.id == character.id:
                return self.times_dict['TAG_CHARACTER']


    def sitrep(self, character: Character):
        """
        ADM asks for a situation report (SITREP).
        If a character is specified then only sitrep that character, otherwise sitrep all responsive characters

        Args:
            character: The character from which to request SITREP, or empty if requesting from all
        """
        time_passed = 0
        if character:
            for isso_character in self.current_isso.scenario.state.characters:
                if isso_character.id == character.id:
                    character.vitals.mental_status = isso_character.vitals.mental_status
                    if character.vitals.mental_status != "UNRESPONSIVE":
                        character.vitals.breathing = isso_character.vitals.breathing
                        character.vitals.conscious = isso_character.vitals.conscious
                        self._reveal_injuries(isso_character, character)
                        character.visited = True
                    time_passed = self.times_dict["SITREP"]
        else:
            # takes time for each responsive character during sitrep
            for curr_character in self.session.scenario.state.characters:
                for isso_character in self.current_isso.scenario.state.characters:
                    if isso_character.id == curr_character.id:
                        curr_character.vitals.mental_status = isso_character.vitals.mental_status
                        if curr_character.vitals.mental_status != "UNRESPONSIVE":
                            curr_character.vitals.conscious = isso_character.vitals.conscious
                            curr_character.vitals.breathing = isso_character.vitals.breathing
                            self._reveal_injuries(isso_character, curr_character)
                            curr_character.visited = True
                        time_passed += self.times_dict["SITREP"]

        return time_passed


    def process_action(self, action: Action):
        """
        Process the action including updating the scenario state.
        The action should be fully validated via `validate_action()`

        Args:
            action: The action to process.
        """
        # keeps track of time passed based on action taken (in seconds)
        time_passed = 0
        # Look up character action is applied to
        character = next((character for character in self.session.scenario.state.characters \
                         if character.id == action.character_id), None)

        parameters = {"action_type": action.action_type, "session_id": self.session.session_id}
        if character:
            parameters['character'] = action.character_id
        match action.action_type:
            case ActionType.APPLY_TREATMENT:
                time_passed = self.apply_treatment(action, character)
                parameters['treatment'] = action.parameters['treatment']
                parameters['location'] = action.parameters['location']
            case ActionType.CHECK_ALL_VITALS:
                time_passed = self.check_all_vitals(character)
            case ActionType.CHECK_PULSE:
                time_passed = self.check_pulse(character)
            case ActionType.CHECK_RESPIRATION:
                time_passed = self.check_respiration(character)
            case ActionType.DIRECT_MOBILE_CHARACTERS:
                time_passed = self.direct_mobile_characters()
            case ActionType.MOVE_TO_EVAC:
                time_passed = self.move_to_evac(character)
            case ActionType.SITREP:
                time_passed = self.sitrep(character)
            case ActionType.TAG_CHARACTER:
                # The tag is specified in the category parameter
                time_passed = self.tag_character(character, action.parameters.get('category'))
                parameters['category'] = action.parameters['category']

        # TODO ITM-72: Enhance character deterioration/amelioration
        # Ultimately, this should update values based DIRECTLY on how the sim does it
        """
        time_elapsed_during_treatment = self.current_isso.character_simulator.treat_character(
            character_id=action.character_id,
            supply=action.justification
        )

        self.time_elapsed_scenario_time += time_elapsed_during_treatment + time_passed
        self.current_isso.character_simulator.update_vitals(time_elapsed_during_treatment)
        self.scenario.state.elapsed_time = self.time_elapsed_scenario_time
        """

        self.session.scenario.state.elapsed_time += time_passed
        # Log the action
        self.session.history.add_history("Take Action", parameters,
                                         self.session.scenario.state.to_dict())
