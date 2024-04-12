import json
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    AvpuLevelEnum,
    Character,
    CharacterTag,
    InjuryLocation,
    InjuryStatusEnum,
    MentalStatusEnum
)
from swagger_server.util import get_swagger_class_enum_values
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
        with open("swagger_server/itm/data/actionTimes.json", 'r') as json_file:
                self.times_dict = json.load(json_file)

    def set_scene(self, scene):
        self.current_scene = scene

    def set_scenario(self, scenario :ITMScenario):
        self.current_scene = scenario.isd.current_scene

    def _reveal_injuries(self, source: Character, target: Character):
        if target.visited:
            pass # Character could be pre-configured visited but with discoverable injuries

        # Add discoverable injuries to target character (with discovered status).
        revealed_injuries = [source_injury for source_injury in source.injuries if source_injury.status == InjuryStatusEnum.DISCOVERABLE]
        for injury in revealed_injuries:
            injury.status = InjuryStatusEnum.DISCOVERED
        target.injuries.extend(revealed_injuries)
        if source.unstructured_postassess:
            target.unstructured = source.unstructured_postassess

    def _proper_treatment(self, treatment: str, injury_name: str, location: str) -> bool:
        # NOTE: Asthmatic, Forehead Scrape, Ear Bleed, an Internal injuries are currently untreatable.
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
            Broken Wrist: Splint
            Hand (Palm) Laceration: Pressure bandage

            Arm Injuries
            Forearm Laceration: Pressure bandage
            Broken Forearm: Splint
            Bicep Puncture: Tourniquet
            Shoulder Puncture: Hemostatic gauze
            Broken Shoulder: Splint

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
            Leg (Shin) Amputation: Tourniquet
            Broken Leg: Splint
            Calf Laceration: Pressure bandage
            Calf Shrapnel: Hemostatic gauze
        """
        match injury_name:
            case 'Amputation':
                return treatment == 'Tourniquet'
            case 'Burn':
                return treatment == 'Burn Dressing'
            case 'Broken Bone':
                return treatment == 'Splint'
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
            character = next((character for character in self.session.state.characters if character.id == action.character_id), None)

        # Validate character when necessary
        if (action.action_type in [ActionTypeEnum.APPLY_TREATMENT, ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_PULSE,
                                   ActionTypeEnum.CHECK_BLOOD_OXYGEN, ActionTypeEnum.CHECK_RESPIRATION, ActionTypeEnum.MOVE_TO_EVAC,
                                   ActionTypeEnum.TAG_CHARACTER]):
            if not action.character_id:
                return False, f'Malformed Action: Missing character_id for {action.action_type}', 400
            elif not character:
                return False, f'Character `{action.character_id}` not found in state', 400

        if action.action_type == ActionTypeEnum.APPLY_TREATMENT:
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
            for supply in self.session.state.supplies:
                if supply.type == supply_used:
                    sufficient_supplies = supply.quantity >= 1
                    break
            if not sufficient_supplies:
                return False, f'Invalid or insufficient `{supply_used}` supplies', 400
        elif action.action_type == ActionTypeEnum.SITREP:
            # sitrep optionally takes a character id
            if action.character_id and not character:
                return False, f'Character `{action.character_id}` not found in state', 400
        elif action.action_type == ActionTypeEnum.TAG_CHARACTER:
            # Requires category parameter
            if not action.parameters or not 'category' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `category` parameter', 400
            else:
                allowed_values = get_swagger_class_enum_values(CharacterTag)
                tag = action.parameters.get('category')
                if not tag in allowed_values:
                    return False, f'Malformed {action.action_type} Action: Invalid Tag `{tag}`', 400
        elif action.action_type == ActionTypeEnum.MOVE_TO_EVAC:
            # Requires evac_id parameter
            if not action.parameters or not 'evac_id' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `evac_id` parameter', 400
        elif action.action_type == ActionTypeEnum.CHECK_ALL_VITALS or action.action_type == ActionTypeEnum.CHECK_PULSE \
            or action.action_type == ActionTypeEnum.CHECK_RESPIRATION or action.action_type == ActionTypeEnum.CHECK_BLOOD_OXYGEN:
            pass # Character was already checked
        elif action.action_type == ActionTypeEnum.DIRECT_MOBILE_CHARACTERS or action.action_type == ActionTypeEnum.END_SCENE \
                or action.action_type == ActionTypeEnum.SEARCH:
            pass # Requires nothing
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        # type checks for possible fields
        if action.unstructured and not isinstance(action.unstructured, str):
            return False, 'Malformed Action: Invalid unstructured description', 400

        if action.justification and not isinstance(action.justification, str):
            return False, 'Malformed Action: Invalid justification', 400

        return True, '', 0


    def _visit_patient(self, patient: Character, patient_template: Character):
        patient.vitals.ambulatory = patient_template.vitals.ambulatory
        patient.vitals.avpu = patient_template.vitals.avpu
        patient.vitals.breathing = patient_template.vitals.breathing
        patient.vitals.conscious = patient_template.vitals.conscious
        patient.vitals.mental_status = patient_template.vitals.mental_status
        self._reveal_injuries(patient_template, patient)
        patient.visited = True


    def apply_treatment(self, action: Action, character: Character):
        """
        Apply a treatment to the specified character.

        Args:
            character: The character to treat
            action: The action which specifies parameters such as the treatment to apply and
            the location to treat.
        """
        # If the treatment treats the injury at the specified location, then change its status to treated.
        supply_used = action.parameters.get('treatment', None)
        attempted_retreatment = False
        for injury in character.injuries:
            if injury.location == action.parameters.get('location', None):
                if injury.status != InjuryStatusEnum.TREATED: # Can't attempt to treat a treated injury
                    if self._proper_treatment(supply_used, injury.name, injury.location):
                        injury.status = InjuryStatusEnum.TREATED
                else:
                    attempted_retreatment = True

        if attempted_retreatment: # Realize the injury is already treated, but no vital/injury discovery happens
            return self.times_dict["treatmentTimes"]["ALREADY_TREATED"]

        # Decrement unreusable supplies and increment time passed during treatment, even if the injury is untreated
        time_passed = 0
        for supply in self.session.state.supplies:
            if supply.type == supply_used:
                if not supply.reusable:
                    supply.quantity -= 1
                if supply_used in self.times_dict["treatmentTimes"]:
                    time_passed = self.times_dict["treatmentTimes"][supply_used]
                break

        # Injuries and certain basic vitals are discovered when a character is treated.
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                self._visit_patient(character, isd_character)

        # Finally, return the elapsed time
        return time_passed


    def check_all_vitals(self, character: Character):
        """
        Check all vitals of the specified character in the scenario.

        Args:
            character: The character to check.
        """
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                character.vitals = isd_character.vitals
                self._reveal_injuries(isd_character, character)
                character.visited = True
                return self.times_dict['CHECK_ALL_VITALS']


    def check_blood_oxygen(self, character: Character):
        """
        Process checking the blood oxygen level (Sp02) of the specified character.

        Args:
            character: The character to check.
        """
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                self._visit_patient(character, isd_character)
                character.vitals.spo2 = isd_character.vitals.spo2
                return self.times_dict['CHECK_BLOOD_OXYGEN']


    def check_pulse(self, character: Character):
        """
        Process checking the pulse (heart rate) of the specified character.

        Args:
            character: The character to check.
        """
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                self._visit_patient(character, isd_character)
                character.vitals.heart_rate = isd_character.vitals.heart_rate
                return self.times_dict['CHECK_PULSE']


    def check_respiration(self, character: Character):
        """
        Check the respiration of the specified character in the scenario.

        Args:
            character: The character to check.
        """
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                self._visit_patient(character, isd_character)
                return self.times_dict['CHECK_RESPIRATION']


    def direct_mobile_characters(self):
        """
        Direct mobile characters to a safe zone (or equivalent).
        """
        for character in self.session.state.characters:
            for isd_character in self.current_scene.state.characters:
                if isd_character.id == character.id:
                    if isd_character.vitals.ambulatory and isd_character.vitals.conscious and \
                    isd_character.vitals.avpu == AvpuLevelEnum.ALERT and \
                    isd_character.vitals.mental_status in [MentalStatusEnum.CALM, MentalStatusEnum.UPSET]:
                        character.vitals.ambulatory = True
                        character.vitals.conscious = True
                        character.vitals.avpu = AvpuLevelEnum.ALERT
                        character.vitals.mental_status = isd_character.vitals.mental_status
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
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                return self.times_dict['TAG_CHARACTER']


    def search(self):
        """
        Search for more characters in the scene.
        """
        return self.times_dict["SEARCH"]


    def sitrep(self, character: Character):
        """
        ADM asks for a situation report (SITREP).
        If a character is specified then only sitrep that character, otherwise sitrep all responsive characters

        Args:
            character: The character from which to request SITREP, or empty if requesting from all
        """
        time_passed = 0
        unresponsive_statuses = [MentalStatusEnum.UNRESPONSIVE, MentalStatusEnum.SHOCK, MentalStatusEnum.CONFUSED]
        if character:
            for isd_character in self.current_scene.state.characters:
                if isd_character.id == character.id:
                    if isd_character.vitals.mental_status not in unresponsive_statuses:
                        self._visit_patient(character, isd_character)
                    else:
                        character.vitals.mental_status = MentalStatusEnum.UNRESPONSIVE
                    time_passed = self.times_dict["SITREP"]
        else:
            # takes time for each responsive character during sitrep
            for curr_character in self.session.state.characters:
                for isd_character in self.current_scene.state.characters:
                    if isd_character.id == curr_character.id:
                        if isd_character.vitals.mental_status not in unresponsive_statuses:
                            self._visit_patient(curr_character, isd_character)
                        else:
                            curr_character.vitals.mental_status = MentalStatusEnum.UNRESPONSIVE
                        time_passed += self.times_dict["SITREP"]

        return time_passed


    def process_action(self, action: Action):
        """
        Process the action including updating the scenario state,
        responding to any probes, and determining if the scene has ended.
        The action should be fully validated via `validate_action()`

        Args:
            action: The action to process.
        """
        # keeps track of time passed based on action taken (in seconds)
        time_passed = 0
        # Look up character action is applied to
        character = next((character for character in self.session.state.characters \
                         if character.id == action.character_id), None)

        parameters = {"action_type": action.action_type, "session_id": self.session.session_id}
        if character:
            parameters['character'] = action.character_id
        match action.action_type:
            case ActionTypeEnum.APPLY_TREATMENT:
                time_passed = self.apply_treatment(action, character)
                parameters['treatment'] = action.parameters['treatment']
                parameters['location'] = action.parameters['location']
            case ActionTypeEnum.CHECK_ALL_VITALS:
                time_passed = self.check_all_vitals(character)
            case ActionTypeEnum.CHECK_BLOOD_OXYGEN:
                time_passed = self.check_blood_oxygen(character)
            case ActionTypeEnum.CHECK_PULSE:
                time_passed = self.check_pulse(character)
            case ActionTypeEnum.CHECK_RESPIRATION:
                time_passed = self.check_respiration(character)
            case ActionTypeEnum.DIRECT_MOBILE_CHARACTERS:
                time_passed = self.direct_mobile_characters()
            case ActionTypeEnum.MOVE_TO_EVAC:
                time_passed = self.move_to_evac(character)
            case ActionTypeEnum.SEARCH:
                time_passed = self.search()
            case ActionTypeEnum.SITREP:
                time_passed = self.sitrep(character)
            case ActionTypeEnum.TAG_CHARACTER:
                # The tag is specified in the category parameter
                time_passed = self.tag_character(character, action.parameters.get('category'))
                parameters['category'] = action.parameters['category']

        # TODO ITM-72: Implement character deterioration/amelioration
        # Ultimately, this should update values based DIRECTLY on how the sim does it

        self.session.state.elapsed_time += time_passed
        # Log the action
        self.session.history.add_history("Take Action", parameters,
                                         self.session.state.to_dict())

        # Tell Scene what happened
        self.current_scene.action_taken(action=action, session_state=self.session.state)
