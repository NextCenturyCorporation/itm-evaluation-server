import json
from copy import deepcopy
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    AvpuLevelEnum,
    Character,
    CharacterTag,
    InjuryLocation,
    InjuryStatusEnum,
    InjuryTypeEnum,
    MentalStatusEnum,
    SupplyTypeEnum
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
        target.injuries.extend(deepcopy(revealed_injuries))
        for injury in target.injuries:
            injury.treatments_required = None
        if source.unstructured_postassess:
            target.unstructured = source.unstructured_postassess

    def __pulse_ox_available(self):
        """
            Check the current state to see if a pulse oximeter is available.
        """
        return any(supply.type == SupplyTypeEnum.PULSE_OXIMETER and supply.quantity >= 1
            for supply in self.session.state.supplies
        )

    def __successful_treatment(self, treatment: str, injury_name: str, location: str) -> bool:
        # NOTE: Asthmatic, Ear Bleed, Traumatic Brain Injury, Open Abdominal Wound, and Internal injuries are currently untreatable.
        # This logic is in sync with the current ITM Simulator, but may diverge at a later date.
        """
            Head Injuries
            Face Laceration: Pressure bandage
            Face Shrapnel: Nasopharyngeal airway
            Ear Bleed: None
            Traumatic Brain Injury: None

            Neck Injuries
            Neck Puncture: Hemostatic gauze
            Neck Burn: Burn Dressing 

            Hand Injuries
            Wrist Amputation: Tourniquet
            Hand (Palm) Laceration: Pressure bandage

            Arm Injuries
            Forearm Laceration: Pressure bandage
            Forearm Burn: Burn Dressing
            Bicep Burn: Burn Dressing
            Bicep Puncture: Tourniquet
            Shoulder Puncture: Hemostatic gauze
            Broken Shoulder: Splint

            Chest Injuries
            Asthmatic: None
            Chest Burn: Burn Dressing
            Chest Collapse: Decompression Needle
            Chest Puncture: Vented Chest Seal

            Stomach Injuries
            Stomach Laceration: Pressure bandage
            Stomach Puncture: Hemostatic gauze
            Side Puncture: Hemostatic gauze
            Open Abdominal Wound: None

            Leg Injuries
            Thigh Puncture: Tourniquet
            Thigh Laceration: Tourniquet
            Thigh Amputation: Tourniquet
            Thigh Burn: Burn Dressing
            Calf Amputation: Tourniquet
            Broken Leg: Splint
            Calf Burn: Burn Dressing
            Calf Laceration: Pressure bandage
            Calf Shrapnel: Pressure bandage
            Calf Puncture: Tourniquet
        """
        match injury_name:
            case InjuryTypeEnum.AMPUTATION:
                return treatment == SupplyTypeEnum.TOURNIQUET
            case InjuryTypeEnum.BURN:
                return treatment == SupplyTypeEnum.BURN_DRESSING
            case InjuryTypeEnum.BROKEN_BONE:
                return treatment == SupplyTypeEnum.SPLINT
            case InjuryTypeEnum.CHEST_COLLAPSE:
                return treatment == SupplyTypeEnum.DECOMPRESSION_NEEDLE
            case InjuryTypeEnum.LACERATION:
                if 'thigh' in location:
                    return treatment == SupplyTypeEnum.TOURNIQUET
                else:
                    return treatment == SupplyTypeEnum.PRESSURE_BANDAGE
            case InjuryTypeEnum.PUNCTURE:
                if 'bicep' in location or 'thigh' in location or 'calf' in location:
                    return treatment == SupplyTypeEnum.TOURNIQUET
                elif 'chest' in location:
                    return treatment == SupplyTypeEnum.VENTED_CHEST_SEAL
                else:
                    return treatment == SupplyTypeEnum.HEMOSTATIC_GAUZE
            case InjuryTypeEnum.SHRAPNEL:
                if 'face' in location:
                    return treatment == SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY
                else:
                    return treatment == SupplyTypeEnum.PRESSURE_BANDAGE
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
        
        if not action.justification:
            return False, 'Invalid or Malformed Action: Missing justification', 400

        if action.parameters and not isinstance(action.parameters, dict):
            return False, 'Malformed Action: Invalid Parameter Structure', 400

        if action.action_type in self.current_scene.restricted_actions or \
            action.action_type == ActionTypeEnum.END_SCENE and not self.current_scene.end_scene_allowed:
            return False, 'Invalid Action: action restricted', 400

        # Validate character
        character = None
        if action.character_id:
            character = next((character for character in self.session.state.characters if character.id == action.character_id), None)
            if not character:
                return False, f'Character `{action.character_id}` not found in state', 400
            elif character.unseen and not action.intent_action and action.action_type not in [ActionTypeEnum.MOVE_TO_EVAC, ActionTypeEnum.MOVE_TO]:
                return False, f'Cannot perform {action.action_type} action with unseen character `{action.character_id}`', 400 
        elif (action.action_type in [ActionTypeEnum.APPLY_TREATMENT, ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_PULSE,
                                   ActionTypeEnum.CHECK_BLOOD_OXYGEN, ActionTypeEnum.CHECK_RESPIRATION, ActionTypeEnum.MOVE_TO_EVAC,
                                   ActionTypeEnum.MOVE_TO, ActionTypeEnum.TAG_CHARACTER]):
            # Character required
            return False, f'Malformed Action: Missing character_id for {action.action_type}', 400

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
        elif action.action_type == ActionTypeEnum.TAG_CHARACTER:
            # Requires category parameter
            if not action.parameters or not 'category' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `category` parameter', 400
            else:
                allowed_values = get_swagger_class_enum_values(CharacterTag)
                tag = action.parameters.get('category')
                if not tag in allowed_values:
                    return False, f'Malformed {action.action_type} Action: Invalid Tag `{tag}`', 400
        elif action.action_type == ActionTypeEnum.MESSAGE:
            # Ensure they chose one of the pre-configured actions and didn't make up their own MESSAGE
            scene_action_ids = [mapping.action_id for mapping in self.current_scene.action_mappings]
            if action.action_id not in scene_action_ids:
                return False, f'Malformed {action.action_type} Action: action_id `{action.action_id}` is not a valid action_id from the current scene', 400
        elif action.action_type == ActionTypeEnum.MOVE_TO:
            # Can only target unseen characters
            if not action.intent_action and not character.unseen:
                return False, f'Can only perform {action.action_type} action with unseen characters, but `{action.character_id}` is not unseen', 400
        elif action.action_type == ActionTypeEnum.MOVE_TO_EVAC:
            # Requires aid_id parameter
            if not action.parameters or not 'aid_id' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `aid_id` parameter', 400
        elif action.action_type == ActionTypeEnum.CHECK_BLOOD_OXYGEN:
            if not self.__pulse_ox_available():
                return False, f'Cannot perform {action.action_type} when no {SupplyTypeEnum.PULSE_OXIMETER} is available.', 400
        elif action.action_type in [ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION, ActionTypeEnum.SITREP]:
            pass # Character was already checked
        elif action.action_type == ActionTypeEnum.DIRECT_MOBILE_CHARACTERS or action.action_type == ActionTypeEnum.END_SCENE \
                or action.action_type == ActionTypeEnum.SEARCH or action.action_type == ActionTypeEnum.CHECK_ALL_VITALS:
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
        if patient.visited:
            return # short-circuit
        patient.vitals.ambulatory = patient_template.vitals.ambulatory
        patient.vitals.avpu = patient_template.vitals.avpu
        patient.vitals.breathing = patient_template.vitals.breathing
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
        supply_used = action.parameters.get('treatment')
        attempted_retreatment = False
        successful_treatment = False
        # Note: Anything added to doesnt_treat_injuries is assumed to be automatically successful, which decrements the supply.
        #       If this is not the case, then add an elif branch below (like BLANKET).
        doesnt_treat_injuries = [SupplyTypeEnum.BLANKET, SupplyTypeEnum.BLOOD, SupplyTypeEnum.EPI_PEN, SupplyTypeEnum.FENTANYL_LOLLIPOP, \
                                 SupplyTypeEnum.IV_BAG, SupplyTypeEnum.PAIN_MEDICATIONS, SupplyTypeEnum.PULSE_OXIMETER]
        if supply_used not in doesnt_treat_injuries:
            for injury in character.injuries:
                if injury.location == action.parameters.get('location'):
                    if injury.status != InjuryStatusEnum.TREATED: # Can't attempt to treat a treated injury
                        if self.__successful_treatment(supply_used, injury.name, injury.location):
                            successful_treatment = True
                            injury.treatments_applied += 1
                            # Find required treatments for the injury
                            for isd_character in self.current_scene.state.characters:
                                if isd_character.id == character.id:
                                    for isd_injury in isd_character.injuries:
                                        if isd_injury.location == injury.location:
                                            treatments_required = isd_injury.treatments_required
                                            break
                            if injury.treatments_applied < treatments_required:
                                injury.status = InjuryStatusEnum.PARTIALLY_TREATED
                            else:
                                injury.status = InjuryStatusEnum.TREATED
                    else:
                        attempted_retreatment = True
                    break
        elif (supply_used == SupplyTypeEnum.BLANKET):
            if character.has_blanket:
                attempted_retreatment = True
            else:
                successful_treatment = True
                character.has_blanket = True
        elif (supply_used != SupplyTypeEnum.PULSE_OXIMETER):
            successful_treatment = True

        if attempted_retreatment: # Realize the injury is already treated, but no vital/injury discovery happens
            return self.times_dict["treatmentTimes"]["ALREADY_TREATED"]

        # Increment time passed during treatment, and decrement unreusable supplies if the injury is successfully treated
        time_passed = 0
        for supply in self.session.state.supplies:
            if supply.type == supply_used:
                if successful_treatment and not supply.reusable:
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
                character.vitals = deepcopy(isd_character.vitals)
                if not self.__pulse_ox_available():
                    character.vitals.spo2 = None
                self._reveal_injuries(isd_character, character)
                character.visited = True
                return self.times_dict[ActionTypeEnum.CHECK_ALL_VITALS]


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
                return self.times_dict[ActionTypeEnum.CHECK_BLOOD_OXYGEN]


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
                return self.times_dict[ActionTypeEnum.CHECK_PULSE]


    def check_respiration(self, character: Character):
        """
        Check the respiration of the specified character in the scenario.

        Args:
            character: The character to check.
        """
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character.id:
                self._visit_patient(character, isd_character)
                return self.times_dict[ActionTypeEnum.CHECK_RESPIRATION]


    def direct_mobile_characters(self):
        """
        Direct mobile characters to a safe zone (or equivalent).
        """
        for character in self.session.state.characters:
            for isd_character in self.current_scene.state.characters:
                if isd_character.id == character.id:
                    if isd_character.vitals.ambulatory and \
                    isd_character.vitals.avpu == AvpuLevelEnum.ALERT and \
                    isd_character.vitals.mental_status in [MentalStatusEnum.CALM, MentalStatusEnum.UPSET]:
                        character.vitals.ambulatory = True
                        character.vitals.avpu = AvpuLevelEnum.ALERT
                        character.vitals.mental_status = isd_character.vitals.mental_status
        return self.times_dict[ActionTypeEnum.DIRECT_MOBILE_CHARACTERS]


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


    def move_to_evac(self, character: Character):
        """
        Move the specified character to the evacuation zone (or equivalent).

        Args:
            character: The character to move to evac
        """
        return self.times_dict[ActionTypeEnum.MOVE_TO_EVAC]


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
                return self.times_dict[ActionTypeEnum.TAG_CHARACTER]


    def search(self):
        """
        Search for more characters.
        """
        # After a search, the ADM is at a new location (which may or may not have patients), so all previous characters become unseen.
        for character in self.session.state.characters:
            character.unseen = True
        return self.times_dict[ActionTypeEnum.SEARCH]


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
                    time_passed = self.times_dict[ActionTypeEnum.SITREP]
        else:
            # takes time for each responsive character during sitrep
            for curr_character in self.session.state.characters:
                for isd_character in self.current_scene.state.characters:
                    if isd_character.id == curr_character.id:
                        if isd_character.vitals.mental_status not in unresponsive_statuses:
                            self._visit_patient(curr_character, isd_character)
                        else:
                            curr_character.vitals.mental_status = MentalStatusEnum.UNRESPONSIVE
                        time_passed += self.times_dict[ActionTypeEnum.SITREP]

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
            case ActionTypeEnum.MOVE_TO:
                time_passed = self.move_to(character)
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
            case _: # Nothing to process except the passage of time
                time_passed = self.times_dict[action.action_type]

        # TODO ITM-72: Implement character deterioration/amelioration
        # Ultimately, this should update values based DIRECTLY on how the sim does it

        self.session.state.elapsed_time += time_passed
        # Log the action
        self.session.history.add_history("Take Action", parameters,
                                         self.session.state.to_dict())

        # Tell Scene what happened
        self.current_scene.action_taken(action=action, session_state=self.session.state)


    def process_intention(self, action: Action):
        """
        Process the intended action including updating the scenario state,
        responding to any probes, and determining if the scene has ended.
        The action should be fully validated via `validate_action()`

        Args:
            action: The action to process.
        """

        # Log the intention
        parameters = {"action_type": action.action_type, "session_id": self.session.session_id}
        self.session.history.add_history("Intend Action", parameters,
                                         self.session.state.to_dict())

        # Tell Scene what happened
        self.current_scene.action_taken(action=action, session_state=self.session.state)
