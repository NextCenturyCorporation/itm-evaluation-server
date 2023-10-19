from swagger_server.models import (
    Action,
    Casualty,
    Scenario,
    State,
    Vitals
)
from .itm_session_scenario_object import (
    ITMSessionScenarioObjectHandler,
    ITMSessionScenarioObject
)
#from.itm_scenario_session import ITMScenarioSession as ITMSession
import itm_utils as utils

class ITMActionHandler:
    """
    Class for processing actions.
    """

    def __init__(self, session):
        """
        Initialize an ITMActionHandler.
        """
        self.session = session
        self.current_isso: ITMSessionScenarioObject = None

    def set_isso(self, isso):
        self.current_isso = isso

    def _reveal_injuries(self, source: Casualty, target: Casualty):
        if target.visited: # Don't reveal injuries in visited casualties
            return

        for source_injury in source.injuries:
            if source_injury.name in self.current_isso.hidden_injury_types and \
                not any(target_injury.name in self.current_isso.hidden_injury_types \
                        for target_injury in target.injuries): \
                            target.injuries.append(source_injury)

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

    # Hide vitals and hidden injuries at start of scenario
    def _clear_hidden_data(self):
        for casualty in self.session.scenario.state.casualties:
            casualty.injuries[:] = \
                [injury for injury in casualty.injuries if injury.name not in self.current_isso.hidden_injury_types]
            casualty.vitals = Vitals()


    def _proper_treatment(self, treatment: str, injury_name: str, location: str) -> bool:
        # NOTE: Asthmatic, Burns, Forehead Scrape, Ear Bleed are currently untreatable

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
                utils.add_history(
                    "Check Pulse",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id},
                    casualty.vitals.hrpmin)
                return
    
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
                utils.add_history(
                    "Check Respiration",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id},
                    casualty.vitals.breathing)
                return

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
                utils.add_history(
                    "Check All Vitals",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id},
                    casualty.vitals.to_dict())
                return

    def apply_treatment(self, action: Action, casualty: Casualty):
        # If appropriate, remove injury from casualty and decrement supplies
        # NOTE: this assumes there is only one injury per location.
        time_passed = 0
        supply_used = action.parameters.get('treatment', None)
        for injury in casualty.injuries:
            if injury.location == action.parameters.get('location', None):
                if self._proper_treatment(supply_used, injury.name, injury.location):
                    casualty.injuries.remove(injury)
                    for supply in self.session.scenario.state.supplies:
                        if supply.type == supply_used:
                            # removing one instance of the supply_used e.g. Tourniquet from supplies list
                            supply.quantity -= 1
                            if supply_used in self.session.times_dict["treatmentTimes"]:
                                # increment time passed during treatment
                                # TBD: should time pass when using the wrong treatment?
                                time_passed += self.session.times_dict["treatmentTimes"][supply_used]
                            break

        # Injuries and certain basic vitals are discovered when a casualty is approached.
        for isso_casualty in self.current_isso.scenario.state.casualties:
            if isso_casualty.id == casualty.id:
                casualty.vitals.breathing = isso_casualty.vitals.breathing
                casualty.vitals.conscious = isso_casualty.vitals.conscious
                casualty.vitals.mental_status = isso_casualty.vitals.mental_status
                self._reveal_injuries(isso_casualty, casualty)
                casualty.visited = True

        # Finally, log the action and return
        utils.add_history(
            "Apply Treatment", {"Session ID": self.session.session_id, "Casualty ID": casualty.id, "Parameters": action.parameters},
            self.session.scenario.state.to_dict())

        return time_passed

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
                utils.add_history(
                    "Tag Casualty",
                    {"Session ID": self.session.session_id, "Casualty ID": casualty.id, "Tag": tag},
                    self.session.scenario.state.to_dict())
                return

    def process_sitrep(self, casualty: Casualty) -> int:
        # if a casualty is specified then only sitrep that casualty
        # otherwise, sitrep all responsive casualties
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
                    time_passed = self.session.times_dict["SITREP"]
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
                        time_passed += self.session.times_dict["SITREP"]

        utils.add_history(
            "Request SITREP", {"Session ID": self.session.session_id,
             "Casualty ID": casualty.id if casualty else "All casualties"},
            self.session.scenario.state.to_dict())

        return time_passed
