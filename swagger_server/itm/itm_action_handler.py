import json
from swagger_server.models import (
    Action,
    Casualty
)
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

    def _reveal_injuries(self, source: Casualty, target: Casualty):
        if target.visited: # Don't reveal injuries in visited casualties
            return

        revealed_injuries = [source_injury for source_injury in source.injuries if self._should_reveal_injury(source_injury, target)]
        target.injuries.extend(revealed_injuries)

        # TODO: develop a system for scenarios to specify changes in plaintext Casualty description
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
            Face Shrapnel: Airway
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
            Stomach Puncture: Hemostatic gauze
            Side Puncture: Hemostatic gauze

            Leg Injuries
            Thigh Puncture: Tourniquet
            Thigh Laceration: Tourniquet
            Shin Amputation: Tourniquet
            Calf Laceration: Pressure bandage
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
                return treatment == 'Nasopharyngeal airway'
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
        # lookup casualty id in state
        casualty = None
        if action.casualty_id:
            casualty = next((casualty for casualty in self.session.scenario.state.casualties if casualty.id == action.casualty_id), None)

        # Validate casualty when necessary
        if (action.action_type in ['APPLY_TREATMENT', 'CHECK_ALL_VITALS', 'CHECK_PULSE', 'CHECK_RESPIRATION', 'MOVE_TO_EVAC', 'TAG_CASUALTY']):
            if not action.casualty_id:
                return False, f'Malformed Action: Missing casualty_id for {action.action_type}', 400
            elif not casualty:
                return False, f'Casualty `{action.casualty_id}` not found in state', 400

        if action.action_type == 'APPLY_TREATMENT':
            # Apply treatment requires a casualty id and parameters (treatment and location)
            # treatment and location
            valid_locations = ['right forearm', 'left forearm', 'right calf', 'left calf', 'right thigh', 'left thigh', 'right stomach', \
                               'left stomach', 'right bicep', 'left bicep', 'right shoulder', 'left shoulder', 'right side', 'left side', \
                               'right chest', 'left chest', 'right wrist', 'left wrist', 'left face', 'right face', 'left neck', \
                               'right neck', 'unspecified']
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
        elif action.action_type == 'SITREP':
            # sitrep optionally takes a casualty id
            if action.casualty_id and not casualty:
                return False, f'Casualty `{action.casualty_id}` not found in state', 400
        elif action.action_type == 'TAG_CASUALTY':
            # Requires category parameter
            if not action.parameters or not 'category' in action.parameters:
                return False, f'Malformed {action.action_type} Action: Missing `category` parameter', 400
            else:
                allowed_values = ['MINIMAL', 'DELAYED', 'IMMEDIATE', 'EXPECTANT']
                tag = action.parameters.get('category')
                if not tag in allowed_values:
                    return f'Malformed {action.action_type} Action: Invalid Tag `{tag}`', 400
        elif action.action_type == 'CHECK_ALL_VITALS' or action.action_type == 'CHECK_PULSE' \
            or action.action_type == 'CHECK_RESPIRATION' or action.action_type == 'MOVE_TO_EVAC':
            pass # Casualty was already checked
        elif action.action_type == 'DIRECT_MOBILE_CASUALTIES' or action.action_type == 'END_SCENARIO':
            pass # Requires nothing
        else:
            return False, f'Invalid action_type `{action.action_type}`', 400

        # type checks for possible fields
        if action.unstructured and not isinstance(action.unstructured, str):
            return False, 'Malformed Action: Invalid unstructured description', 400

        if action.justification and not isinstance(action.justification, str):
            return False, 'Malformed Action: Invalid justification', 400

        return True, '', 0


    def apply_treatment(self, action: Action, casualty: Casualty):
        """
        Apply a treatment to the specified casualty.

        Args:
            casualty: The casualty to treat
            action: The action which specifies parameters such as the treatment to apply and
            the location to treat.
        """
        # Remove injury from casualty if the treatment treats the injury at the specified location
        # NOTE: this assumes there is only one injury per location.
        supply_used = action.parameters.get('treatment', None)
        for injury in casualty.injuries:
            if injury.location == action.parameters.get('location', None):
                if self._proper_treatment(supply_used, injury.name, injury.location):
                    casualty.injuries.remove(injury)

        # Decrement supplies and increment time passed during treatment, even if the injury is untreated
        time_passed = 0
        for supply in self.session.scenario.state.supplies:
            if supply.type == supply_used:
                supply.quantity -= 1
                if supply_used in self.times_dict["treatmentTimes"]:
                    time_passed = self.times_dict["treatmentTimes"][supply_used]
                break

        # Injuries and certain basic vitals are discovered when a casualty is treated.
        for isso_casualty in self.current_isso.scenario.state.casualties:
            if isso_casualty.id == casualty.id:
                casualty.vitals.breathing = isso_casualty.vitals.breathing
                casualty.vitals.conscious = isso_casualty.vitals.conscious
                casualty.vitals.mental_status = isso_casualty.vitals.mental_status
                self._reveal_injuries(isso_casualty, casualty)
                casualty.visited = True

        # Finally, log the action and return the elapsed time
        self.session.history.add_history(
            "Apply Treatment", {"Session ID": self.session.session_id,
                                "Casualty ID": casualty.id, "Parameters": action.parameters},
            self.session.scenario.state.to_dict())
        return time_passed


    def check_all_vitals(self, casualty: Casualty):
        """
        Check all vitals of the specified casualty in the scenario.

        Args:
            casualty: The casualty to check.
        """
        for isso_casualty in self.current_isso.scenario.state.casualties:
            if isso_casualty.id == casualty.id:
                casualty.vitals = isso_casualty.vitals
                self._reveal_injuries(isso_casualty, casualty)
                casualty.visited = True
                self.session.history.add_history(
                    "Check All Vitals",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id},
                    casualty.vitals.to_dict())
                return self.times_dict['CHECK_ALL_VITALS']


    def check_pulse(self, casualty: Casualty):
        """
        Process checking the pulse (heart rate) of the specified casualty.

        Args:
            casualty: The casualty to check.
        """
        for isso_casualty in self.current_isso.scenario.state.casualties:
            if isso_casualty.id == casualty.id:
                casualty.vitals.breathing = isso_casualty.vitals.breathing
                casualty.vitals.conscious = isso_casualty.vitals.conscious
                casualty.vitals.mental_status = isso_casualty.vitals.mental_status
                casualty.vitals.hrpmin = isso_casualty.vitals.hrpmin
                self._reveal_injuries(isso_casualty, casualty)
                casualty.visited = True
                self.session.history.add_history(
                    "Check Pulse",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id},
                    casualty.vitals.hrpmin)
                return self.times_dict['CHECK_PULSE']


    def check_respiration(self, casualty: Casualty):
        """
        Check the respiration of the specified casualty in the scenario.

        Args:
            casualty: The casualty to check.
        """
        for isso_casualty in self.current_isso.scenario.state.casualties:
            if isso_casualty.id == casualty.id:
                casualty.vitals.breathing = isso_casualty.vitals.breathing
                casualty.vitals.conscious = isso_casualty.vitals.conscious
                casualty.vitals.mental_status = isso_casualty.vitals.mental_status
                self._reveal_injuries(isso_casualty, casualty)
                casualty.visited = True
                self.session.history.add_history(
                    "Check Respiration",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id},
                    casualty.vitals.breathing)
                return self.times_dict['CHECK_RESPIRATION']


    def direct_mobile_casualties(self):
        """
        Direct mobile casualties to a safe zone (or equivalent).
        """
        self.session.history.add_history(
            "Direct Mobile Casualties", {"Session ID": self.session.session_id},
            self.session.scenario.state.to_dict())
        return self.times_dict["DIRECT_MOBILE_CASUALTIES"]


    def move_to_evac(self, casualty: Casualty):
        """
        Move the specified casualty to the evacuation zone (or equivalent).

        Args:
            casualty: The casualty to move to evac
        """
        self.session.history.add_history(
            "Move to EVAC", {"Session ID": self.session.session_id, "Casualty ID": casualty.id},
            self.session.scenario.state.to_dict())
        return self.times_dict["MOVE_TO_EVAC"]


    def tag_casualty(self, casualty: Casualty, tag: str):
        """
        Tag the specified casualty with a triage category

        Args:
            casualty: The casualty to tag
            tag: The tag to assign to the casualty.
        """
        casualty.tag = tag
        for isso_casualty in self.current_isso.scenario.state.casualties:
            if isso_casualty.id == casualty.id:
                self.session.history.add_history(
                    "Tag Casualty",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id, "Tag": tag},
                    self.session.scenario.state.to_dict())
                return self.times_dict['TAG_CASUALTY']


    def sitrep(self, casualty: Casualty):
        """
        ADM asks for a situation report (SITREP).
        If a casualty is specified then only sitrep that casualty, otherwise sitrep all responsive casualties

        Args:
            casualty: The casualty from which to request SITREP, or empty if requesting from all
        """
        time_passed = 0
        if casualty:
            for isso_casualty in self.current_isso.scenario.state.casualties:
                if isso_casualty.id == casualty.id:
                    casualty.vitals.mental_status = isso_casualty.vitals.mental_status
                    if casualty.vitals.mental_status != "UNRESPONSIVE":
                        casualty.vitals.breathing = isso_casualty.vitals.breathing
                        casualty.vitals.conscious = isso_casualty.vitals.conscious
                        self._reveal_injuries(isso_casualty, casualty)
                        casualty.visited = True
                    time_passed = self.times_dict["SITREP"]
        else:
            # takes time for each responsive casualty during sitrep
            for curr_casualty in self.session.scenario.state.casualties:
                for isso_casualty in self.current_isso.scenario.state.casualties:
                    if isso_casualty.id == curr_casualty.id:
                        curr_casualty.vitals.mental_status = isso_casualty.vitals.mental_status
                        if curr_casualty.vitals.mental_status != "UNRESPONSIVE":
                            curr_casualty.vitals.conscious = isso_casualty.vitals.conscious
                            curr_casualty.vitals.breathing = isso_casualty.vitals.breathing
                            self._reveal_injuries(isso_casualty, casualty)
                            curr_casualty.visited = True
                        time_passed += self.times_dict["SITREP"]

        self.session.history.add_history(
            "Request SITREP", {"Session ID": self.session.session_id,
             "Casualty ID": casualty.id if casualty else "All casualties"},
            self.session.scenario.state.to_dict())

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
        # Look up casualty action is applied to
        casualty = next((casualty for casualty in self.session.scenario.state.casualties \
                         if casualty.id == action.casualty_id), None)

        match action.action_type:
            case 'APPLY_TREATMENT':
                time_passed = self.apply_treatment(action, casualty)
            case 'CHECK_ALL_VITALS':
                time_passed = self.check_all_vitals(casualty)
            case 'CHECK_PULSE':
                time_passed = self.check_pulse(casualty)
            case 'CHECK_RESPIRATION':
                time_passed = self.check_respiration(casualty)
            case 'DIRECT_MOBILE_CASUALTIES':
                time_passed = self.direct_mobile_casualties()
            case 'MOVE_TO_EVAC':
                time_passed = self.move_to_evac(casualty)
            case 'SITREP':
                time_passed = self.sitrep(casualty)
            case 'TAG_CASUALTY':
                # The tag is specified in the category parameter
                time_passed = self.tag_casualty(casualty, action.parameters.get('category'))

        # TODO ITM-72: Enhance casualty deterioration/amelioration
        # Ultimately, this should update values based DIRECTLY on how the sim does it
        """
        time_elapsed_during_treatment = self.current_isso.casualty_simulator.treat_casualty(
            casualty_id=action.casualty_id,
            supply=action.justification
        )

        self.time_elapsed_scenario_time += time_elapsed_during_treatment + time_passed
        self.current_isso.casualty_simulator.update_vitals(time_elapsed_during_treatment)
        self.scenario.state.elapsed_time = self.time_elapsed_scenario_time
        """
        self.session.scenario.state.elapsed_time += time_passed
