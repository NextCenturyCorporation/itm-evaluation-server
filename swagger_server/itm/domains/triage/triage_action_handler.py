import json
import logging
from copy import deepcopy
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    AvpuLevelEnum,
    Character,
    CharacterTagEnum,
    InjuryLocationEnum,
    InjuryStatusEnum,
    InjuryTypeEnum,
    MentalStatusEnum,
    SupplyTypeEnum
)
from swagger_server.util import get_swagger_class_enum_values
from swagger_server.itm import ITMActionHandler

class TriageActionHandler(ITMActionHandler):
    """
    Class for validating and processing triage actions.
    """
    def __init__(self, session):
        """
        Initialize an TriageActionHandler.
        """
        super().__init__(session)

    def load_action_times(self):
        super().load_action_times()
        # Add triage-specific action times
        filespec = self.session.domain_config.get_action_time_filespec()
        with open(filespec, 'r') as json_file:
            self.times_dict.update(json.load(json_file))

    def _reveal_injuries(self, source: Character, target: Character):
        if target.visited:
            return # Visited characters have already had their injuries revealed.

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
            Face Abrasion: Pressure bandage
            Ear Bleed: None
            Traumatic Brain Injury: None

            Neck Injuries
            Neck Laceration: Hemostatic gauze
            Neck Puncture: Hemostatic gauze
            Neck Burn: Burn Dressing 

            Wrist Injuries
            Wrist Amputation: Tourniquet
            Hand (Palm) Laceration: Pressure bandage

            Arm Injuries
            Forearm Puncture: Tourniquet
            Forearm Laceration: Pressure bandage
            Forearm Burn: Burn Dressing
            Forearm Abrasion: Pressure bandage
            Bicep Burn: Burn Dressing
            Bicep Laceration: Tourniquet
            Bicep Puncture: Tourniquet
            Bicep Abrasion: Pressure bandage
            Shoulder Laceration: Hemostatic gauze
            Shoulder Puncture: Hemostatic gauze
            Broken Shoulder: Splint

            Chest Injuries
            Asthmatic: None
            Chest Burn: Burn Dressing
            Chest Collapse: Decompression Needle
            Chest Laceration: Hemostatic gauze
            Chest Puncture: Vented Chest Seal

            Stomach Injuries
            Stomach Laceration: Hemostatic gauze
            Stomach Puncture: Hemostatic gauze
            Side Puncture: Hemostatic gauze
            Open Abdominal Wound: None

            Leg Injuries
            Thigh Puncture: Tourniquet
            Thigh Laceration: Tourniquet
            Thigh Amputation: Tourniquet
            Thigh Burn: Burn Dressing
            Thigh Abrasion: Pressure bandage
            Calf Amputation: Tourniquet
            Broken Leg: Splint
            Calf Burn: Burn Dressing
            Calf Laceration: Pressure bandage
            Calf Shrapnel: Pressure bandage
            Calf Puncture: Tourniquet
            Calf Abrasion: Pressure bandage
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
            case InjuryTypeEnum.ABRASION:
                return treatment == SupplyTypeEnum.PRESSURE_BANDAGE
            case InjuryTypeEnum.LACERATION:
                if location in ['thigh', 'bicep']:
                    return treatment == SupplyTypeEnum.TOURNIQUET
                elif location in ['stomach', 'chest', 'neck', 'shoulder']:
                    return treatment == SupplyTypeEnum.HEMOSTATIC_GAUZE
                else:
                    return treatment == SupplyTypeEnum.PRESSURE_BANDAGE
            case InjuryTypeEnum.PUNCTURE:
                if location in ['forearm', 'bicep', 'thigh', 'calf']:
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


    def validate_domain_action(self, action: Action, character: Character):
        """
        Validate that action is a valid, well-formed action.
        The action has already passed base level validation.

        Args:
            action: The action to validate.
            character: The character specified in the action, if any
        """

        # Validate character
        if action.character_id:
            character = next((character for character in self.session.state.characters if character.id == action.character_id), None)
            if character.unseen and not action.intent_action and action.action_type != ActionTypeEnum.MOVE_TO_EVAC:
                return False, f'Cannot perform {action.action_type} action with unseen character `{action.character_id}`', 400 
        elif (action.action_type in [ActionTypeEnum.APPLY_TREATMENT, ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_PULSE,
                                   ActionTypeEnum.CHECK_BLOOD_OXYGEN, ActionTypeEnum.CHECK_RESPIRATION, ActionTypeEnum.MOVE_TO_EVAC,
                                   ActionTypeEnum.TAG_CHARACTER]):
            # Character required
            return False, f'Malformed Action: Missing character_id for {action.action_type}', 400

        if action.action_type == ActionTypeEnum.APPLY_TREATMENT:
            # Apply treatment requires a character id and parameters (treatment and location)
            # treatment and location
            valid_locations = get_swagger_class_enum_values(InjuryLocationEnum)
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
                allowed_values = get_swagger_class_enum_values(CharacterTagEnum)
                tag = action.parameters.get('category')
                if not tag in allowed_values:
                    return False, f'Malformed {action.action_type} Action: Invalid Tag `{tag}`', 400
        elif action.action_type == ActionTypeEnum.MOVE_TO_EVAC:
            # Requires aid_id parameter
            if not action.parameters or not 'aid_id' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `aid_id` parameter', 400
        elif action.action_type == ActionTypeEnum.CHECK_BLOOD_OXYGEN:
            if not self.__pulse_ox_available():
                return False, f'Cannot perform {action.action_type} when no {SupplyTypeEnum.PULSE_OXIMETER} is available.', 400
        elif action.action_type in [ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION, ActionTypeEnum.SITREP]:
            pass # Character was already checked
        elif action.action_type in [ActionTypeEnum.DIRECT_MOBILE_CHARACTERS, ActionTypeEnum.CHECK_ALL_VITALS]:
            pass # Requires nothing
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        return True, '', 0


    def _visit_patient(self, patient: Character, patient_template: Character):
        if patient.visited:
            return # short-circuit
        patient.vitals.ambulatory = patient_template.vitals.ambulatory
        patient.vitals.avpu = patient_template.vitals.avpu
        patient.vitals.breathing = patient_template.vitals.breathing
        patient.vitals.mental_status = patient_template.vitals.mental_status
        patient.vitals.triss = patient_template.vitals.triss
        self._reveal_injuries(patient_template, patient)
        patient.visited = True

    # Certain unsuccessful treatments still use supplies
    def __check_unsuccessful_treatment(self, supply_used, injury_name, location):
        if supply_used == SupplyTypeEnum.HEMOSTATIC_GAUZE:
            # Certain misapplications of hemostatic cause will consume the gauze but not treat the injury.
            if injury_name in [InjuryTypeEnum.ABRASION, InjuryTypeEnum.LACERATION,
                               InjuryTypeEnum.SHRAPNEL, InjuryTypeEnum.OPEN_ABDOMINAL_WOUND]:
                return True
            elif injury_name == InjuryTypeEnum.PUNCTURE:
                return 'bicep' in location or 'forearm' in location or 'thigh' in location or 'calf' in location
        elif supply_used == SupplyTypeEnum.PRESSURE_BANDAGE:
            if injury_name == InjuryTypeEnum.OPEN_ABDOMINAL_WOUND:
                return True
        return False

    def __check_downstream_injuries(self, character_id, all_injuries, treated_injury):
        """
        Certain successful tourniquet treatments also treat downstream injuries.

        Args:
            character_id: The id of the character being treated
            all_injuries: The full list of character injuries
            treated_injury: The injury that was treated in the current action
        """
        IRRELEVANT = 'irrelevant'
        treated_part = 'bicep' if 'bicep' in treated_injury.location else 'thigh' if 'thigh' in treated_injury.location \
            else 'forearm' if 'forearm' in treated_injury.location else IRRELEVANT
        treated_injury_type = 'puncture' if treated_injury.name == InjuryTypeEnum.PUNCTURE \
            else 'laceration' if treated_injury.name == InjuryTypeEnum.LACERATION else IRRELEVANT
        if treated_part is IRRELEVANT or treated_injury_type is IRRELEVANT:
            return # Doesn't apply
        treated_side = 'right' if 'right' in treated_injury.location else 'left'
        downstream_injury = None

        for injury in all_injuries:
            name = 'puncture' if injury.name == InjuryTypeEnum.PUNCTURE \
                else 'amputation' if injury.name == InjuryTypeEnum.AMPUTATION else IRRELEVANT
            side = 'right' if 'right' in injury.location else 'left'
            part = 'forearm' if 'forearm' in injury.location else 'wrist' if 'wrist' in injury.location \
                else 'calf' if 'calf' in injury.location else IRRELEVANT
            if side != treated_side or part is IRRELEVANT or name is IRRELEVANT:
                continue # Doesn't apply

            if treated_part == 'bicep' and treated_injury_type == 'puncture':
                # Applying a tourniquet to a bicep puncture also treats a forearm puncture or wrist amputation.
                if (part == 'forearm' and name == 'puncture') or (part == 'wrist' and name == 'amputation'):
                    downstream_injury = injury
            elif treated_part == 'forearm' and treated_injury_type == 'puncture':
                # Applying a tourniquet to a forearm puncture also treats a wrist amputation.
                if part == 'wrist' and name == 'amputation':
                    downstream_injury = injury
            elif treated_part == 'thigh' and (treated_injury_type == 'puncture' or treated_injury_type == 'laceration'):
                # Applying a tourniquet to a thigh also treats a calf puncture or calf amputation
                if part == 'calf' and name in ['puncture', 'amputation']:
                    downstream_injury = injury

        if downstream_injury:
            self.__treat_injury(character_id, downstream_injury, SupplyTypeEnum.TOURNIQUET)


    def __treat_injury(self, character_id, injury, supply_used):
        logging.info(f"Successfully treated {injury.name} at {injury.location} with {supply_used}.")
        injury.treatments_applied += 1
        # Find required treatments for the injury
        for isd_character in self.current_scene.state.characters:
            if isd_character.id == character_id:
                for isd_injury in isd_character.injuries:
                    if isd_injury.location == injury.location and isd_injury.name == injury.name:
                        treatments_required = isd_injury.treatments_required
                        break
        if injury.treatments_applied < treatments_required:
            injury.status = InjuryStatusEnum.PARTIALLY_TREATED
        else:
            injury.status = InjuryStatusEnum.TREATED
        logging.debug(f"Setting injury {injury.name} to status {injury.status}")


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
        treatment_location = action.parameters.get('location')
        attempted_retreatment = False
        successful_treatment = False
        consumed_supply = False
        # Note: Anything added to doesnt_treat_injuries is assumed to be automatically successful, which decrements the supply.
        #       If this is not the case, then add an elif branch below (like BLANKET).
        doesnt_treat_injuries = [SupplyTypeEnum.BLANKET, SupplyTypeEnum.BLOOD, SupplyTypeEnum.EPI_PEN, SupplyTypeEnum.FENTANYL_LOLLIPOP, \
                                 SupplyTypeEnum.IV_BAG, SupplyTypeEnum.PAIN_MEDICATIONS, SupplyTypeEnum.PULSE_OXIMETER]
        if supply_used not in doesnt_treat_injuries:
            for injury in character.injuries:
                logging.debug(f"Processing injury {injury.name} at location {injury.location} with status {injury.status} with supply {supply_used}.")
                if injury.location == treatment_location:
                    logging.debug(f"Found {injury.name} injury at location {injury.location}.")
                    if injury.status != InjuryStatusEnum.TREATED: # Can't attempt to treat a treated injury
                        logging.debug(f"Attempting to treat injury {injury.name} at location {injury.location} with {supply_used}.")
                        if self.__successful_treatment(supply_used, injury.name, injury.location):
                            successful_treatment = True
                            self.__treat_injury(character.id, injury, supply_used)
                            if supply_used == SupplyTypeEnum.TOURNIQUET:
                                self.__check_downstream_injuries(character.id, character.injuries, injury)
                        else:
                            logging.info(f"Unsuccessfully treated {injury.name} at {injury.location} with {supply_used}.")
                            consumed_supply = self.__check_unsuccessful_treatment(supply_used, injury.name, injury.location)
                    else:
                        logging.debug(f"Attempted retreatment of injury {injury.name} at location {injury.location}.")
                        attempted_retreatment = True
            if not successful_treatment:
                if supply_used == SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY:
                    # Airways can be placed in the nose even if there's no injury, consuming supplies.
                    # Only one airway should be able to be placed per nostril, see ITM-643.
                    consumed_supply = treatment_location == InjuryLocationEnum.RIGHT_FACE or InjuryLocationEnum.LEFT_FACE
        elif (supply_used == SupplyTypeEnum.BLANKET):
            if character.has_blanket:
                attempted_retreatment = True
            else:
                successful_treatment = True
                character.has_blanket = True
        elif (supply_used != SupplyTypeEnum.PULSE_OXIMETER):
            successful_treatment = True

        if attempted_retreatment and not successful_treatment: # Realize the injury is already treated, but no vital/injury discovery happens
            return self.times_dict["treatmentTimes"]["ALREADY_TREATED"]

        # Increment time passed during treatment, and decrement unreusable supplies if the injury is successfully treated
        time_passed = 0
        for supply in self.session.state.supplies:
            if supply.type == supply_used:
                if (successful_treatment or consumed_supply) and not supply.reusable:
                    supply.quantity -= 1
                    logging.debug(f"Decrementing {supply.type} to {supply.quantity}")
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
        Process checking the blood oxygen level (spo2) of the specified character.

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
                parameters['aid_id'] = action.parameters['aid_id']
            case ActionTypeEnum.SITREP:
                time_passed = self.sitrep(character)
            case ActionTypeEnum.TAG_CHARACTER:
                # The tag is specified in the category parameter
                time_passed = self.tag_character(character, action.parameters.get('category'))
                parameters['category'] = action.parameters['category']
            case _: # Nothing to process except the passage of time
                time_passed = self.times_dict[action.action_type]

        return time_passed


    # Collect triage-specific parameters for the intended action for logging purposes
    def add_intent_parameters(self, action: Action, parameters: dict):
        super().add_intent_parameters(action, parameters)
        match action.action_type:
            case ActionTypeEnum.APPLY_TREATMENT:
                parameters['treatment'] = action.parameters['treatment']
                parameters['location'] = action.parameters['location']
            case ActionTypeEnum.MOVE_TO_EVAC:
                parameters['aid_id'] = action.parameters['aid_id']
            case ActionTypeEnum.TAG_CHARACTER:
                parameters['category'] = action.parameters['category']
