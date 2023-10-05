import time
import uuid
import random
import os
import connexion
import json
from typing import List, Union
from copy import deepcopy
from swagger_server.models import (
    Action,
    AlignmentTarget,
    Casualty,
    Scenario,
    State,
    Vitals
)
from swagger_server.models.probe_response import ProbeResponse
from .itm_database.itm_mongo import MongoDB
from .itm_session_scenario_object import (
    ITMSessionScenarioObjectHandler,
    ITMSessionScenarioObject
)

class ITMScenarioSession:
    """
    Class for representing and manipulating a simulation scenario session.
    """

    def __init__(self):
        """
        Initialize an ITMScenarioSession.
        """
        self.session_id = None
        self.adm_name = ''
        self.time_started = 0
        self.time_elapsed_realtime = 0
        self.time_elapsed_scenario_time = 0

        # isso is short for ITM Session Scenario Object
        self.session_type = ''
        self.current_isso: ITMSessionScenarioObject = None
        self.current_isso_index = 0
        self.session_issos = []
        self.number_of_scenarios = None
        self.custom_scenario_count = 0 # when scenario_id is specified in start_scenario
        self.scenario: Scenario = None
        self.first_answer: bool = True
        # hacky stuff for adept
        self.casualty_ids = []
        self.adept_evac_happened = False
        # adept or ST
        self.scenario_rules = ""

        # This determines whether the server makes calls to TA1
        self.ta1_integration = False
    
        # This calls the dashboard's MongoDB
        self.save_to_database = False
        HOST = os.getenv("DB_HOST")
        if HOST is None or HOST == "":
            HOST = "localhost"
        self.mongo_db = MongoDB('dashroot', 'dashr00tp@ssw0rd',
                                HOST, '27017', 'dashboard')
        
        with open("swagger_server/itm/treatment_times_config/actionTimes.json", 'r') as json_file:
                self.times_dict = json.load(json_file)

        self.history = []


    def _add_history(self,
                    command: str,
                    parameters: dict,
                    response: Union[dict, str]) -> None:
        """
        Add a command to the history of the scenario session.

        Args:
            command: The command executed.
            parameters: The parameters passed to the command.
            response: The response from the command.
        """
        history = {
            "command": command,
            "parameters": parameters,
            "response": response
        }
        self.history.append(history)


    def _check_scenario_id(self, scenario_id: str) -> None:
        """
        Check if the provided scenario ID matches the session's scenario ID.

        Args:
            scenario_id: The scenario ID to compare.
        """
        if not scenario_id == self.scenario.id:
            return False, f'Scenario ID {scenario_id} not found', 404
        return True, '', 0


    def _validate_action(self, action: Action) -> None:
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
            casualty = next((casualty for casualty in self.scenario.state.casualties if casualty.id == action.casualty_id), None)

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
            # Ensure there are sufficient Supplies for the treatment. This check also catches invalid treatments.
            supply_used = action.parameters.get('treatment', None)
            sufficient_supplies = False
            for supply in self.scenario.state.supplies:
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

    def _end_scenario(self):
        """
        End the current scenario and store history to mongo and json file.
        """
        self.scenario.state.scenario_complete = True
        self.adept_evac_happened = False
        self.first_answer = True

        if self.ta1_integration == True:
            alignment_target_session_alignment = \
                self.current_isso.ta1_controller.get_session_alignment()
            print(f"--> Got session alignment {alignment_target_session_alignment} from TA1.")
            self._add_history(
                "TA1 Session Alignment",
                {"Session ID": self.current_isso.ta1_controller.session_id,
                "Target ID": self.current_isso.ta1_controller.alignment_target_id},
                alignment_target_session_alignment
            )
        else:
            print("--> Got session alignment from TA1.")

        if self.save_to_database:
            self.mongo_db.insert_data('scenarios', self.scenario.to_dict())
            insert_id = self.mongo_db.insert_data('test', {"history": self.history})
            retrieved_data = self.mongo_db.retrieve_data('test', insert_id)
            # Write the retrieved data to a local JSON file
            self.mongo_db.write_to_json_file(retrieved_data)
        self.history = []


    def _get_realtime_elapsed_time(self) -> float:
        """
        Return the elapsed time since the session started.

        Returns:
            The elapsed time in seconds as a float.
        """
        if self.time_started:
            self.time_elapsed_realtime = time.time() - self.time_started
        return round(self.time_elapsed_realtime, 2)


    def _get_sub_directory_names(self, directory):
        """
        Return the names of all of the subdirectories inside of the
        parameter directory.

        Args:
            directory: The directory to search inside of for subdirectories.
        """

        directories = []
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                directories.append(item)
        return directories

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


    def _reveal_injuries(self, source: Casualty, target: Casualty):
        if target.visited: # Don't reveal injuries in visited casualties
            return

        for source_injury in source.injuries:
            if source_injury.name in self.current_isso.hidden_injury_types and \
                not any(target_injury.name in self.current_isso.hidden_injury_types \
                        for target_injury in target.injuries): \
                            target.injuries.append(source_injury)

        # TODO: develop a system for scenarios to specify changes in plaintext Casualty description
        if self.scenario_rules == "SOARTECH":
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
        for casualty in self.scenario.state.casualties:
            casualty.injuries[:] = \
                [injury for injury in casualty.injuries if injury.name not in self.current_isso.hidden_injury_types]
            casualty.vitals = Vitals()


    def get_alignment_target(self, scenario_id: str) -> AlignmentTarget:
        """
        Get the alignment target for a specific scenario.

        Args:
            scenario_id: The ID of the scenario.

        Returns:
            The alignment target for the specified scenario as an AlignmentTarget object.
        """

        # Check for a valid scenario_id
        (successful, message, code) = self._check_scenario_id(scenario_id)
        if not successful:
            return message, code
        if self.scenario.session_complete:
            return 'Scenario Complete', 400
        return self.current_isso.alignment_target_reader.alignment_target


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
                self._add_history(
                    "Check Pulse",
                    {"Session ID": self.session_id, "Casualty ID": casualty.id},
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
                self._add_history(
                    "Check Respiration",
                    {"Session ID": self.session_id, "Casualty ID": casualty.id},
                    casualty.vitals.breathing)
                return


    def get_scenario_state(self, scenario_id: str) -> State:
        """
        Get the current state of the scenario.

        Args:
            scenario_id: The ID of the scenario.

        Returns:
            The current state of the scenario as a State object.
        """

        # Check for a valid scenario_id
        (successful, message, code) = self._check_scenario_id(scenario_id)
        if not successful:
            return message, code

        self._add_history(
            "Get Scenario State",
            {"Session ID": self.session_id, "Scenario ID": scenario_id},
            self.scenario.state.to_dict())

        return self.scenario.state


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
                self._add_history(
                    "Check All Vitals",
                    {"Session ID": self.session_id, "Casualty ID": casualty.id},
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
                    for supply in self.scenario.state.supplies:
                        if supply.type == supply_used:
                            # removing one instance of the supply_used e.g. Tourniquet from supplies list
                            supply.quantity -= 1
                            if supply_used in self.times_dict["treatmentTimes"]:
                                # increment time passed during treatment
                                # TBD: should time pass when using the wrong treatment?
                                time_passed += self.times_dict["treatmentTimes"][supply_used]
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
        self._add_history(
            "Apply Treatment", {"Session ID": self.session_id, "Casualty ID": casualty.id, "Parameters": action.parameters},
            self.scenario.state.to_dict())

        return time_passed


    def start_scenario(self, scenario_id: str=None) -> Scenario:
        """
        Start a new scenario.

        Args:
            scenario_id: a scenario ID to start, used internally by TA3

        Returns:
            The started scenario as a Scenario object.
        """

        if scenario_id:
            if self.adm_name != 'TA3':
                raise connexion.ProblemException(status=403, title="Forbidden", detail="Specifying a scenario ID is unauthorized")
            if self.custom_scenario_count >= self.number_of_scenarios:
                return self._end_session() # We've executed the specified number of custom scenarios
            index = 0
            self.current_isso = None
            for isso in self.session_issos:
                if scenario_id == isso.scenario.id:
                    self.current_isso = isso
                    self.current_isso_index = index
                    self.custom_scenario_count += 1
                    break
                index += 1
            if self.current_isso is None:
                return f'Scenario ID `{scenario_id}` does not exist for `{self.session_type}`', 404
        else:
            if self.current_isso_index < len(self.session_issos):
                self.current_isso: ITMSessionScenarioObject = self.session_issos[self.current_isso_index]
            else:
                return self._end_session() # No more scenarios means we can end the session

        try:
            self.scenario = deepcopy(self.current_isso.scenario)
            self._clear_hidden_data()
            self.current_isso_index += 1

            # the rules are different... so we need to know which group the scenario is from
            if self.scenario.id.__contains__("adept"):
                self.scenario_rules = "ADEPT"
            else:
                self.scenario_rules = "SOARTECH"

            self._add_history(
                "Start Scenario",
                {"Session ID": self.session_id, "ADM Name": self.adm_name},
                self.scenario.to_dict())

            if self.ta1_integration == True:
                ta1_session_id = self.current_isso.ta1_controller.new_session()
                self._add_history(
                    "TA1 Session ID", {}, ta1_session_id
                )
                print(f"--> Got new session_id {ta1_session_id} from TA1.")
                scenario_alignment = self.current_isso.ta1_controller.get_alignment_target()
                print(f"--> Got alignment target {scenario_alignment} from TA1.")
                self._add_history(
                    "TA1 Alignment Target Data",
                    {"Session ID": self.current_isso.ta1_controller.session_id,
                    "Scenario ID": self.current_isso.scenario.id},
                    scenario_alignment
                )
            else:
                print("--> Got alignment target from TA1.")

            return self.scenario
        except:
            print("--> Exception getting next scenario; ending session.")
            return self._end_session() # Exception here ends the session

    def _end_session(self) -> Scenario:
        self.__init__()
        return Scenario(session_complete=True, id='', name='',
                        start_time=None, state=None, triage_categories=None)

    def start_session(self, adm_name: str, session_type: str, kdma_training: bool, max_scenarios=None) -> str:
        """
        Start a new session.

        Args:
            adm_name: The adm name associated with the scenario.
            session_type: The type of scenarios either soartech, adept, or eval
            max_scenarios: The max number of scenarios presented during the session

        Returns:
            A new session Id to use in subsequent calls
        """
        if session_type not in ['adept', 'soartech', 'eval']:
            return (
                f'Invalid session type `{session_type}`. Must be "adept, soartech, or eval"',
                400
            )

        # Re-use current session for same ADM after a client crash
        if self.session_id == None:
            self.session_id = str(uuid.uuid4())
        elif self.adm_name == adm_name:
            print(f"--> Re-using session {self.session_id} for ADM {self.adm_name}")
            self._add_history(
                "Abort Session", {"Session ID": self.session_id, "ADM Name": self.adm_name}, None)
            self.__init__()
            self.session_id = str(uuid.uuid4()) # but assign new session_id for clarity in logs/history
        else:
            return 'System Overload', 503 # itm_ta2_eval_controller should prevent this

        self.kdma_training = kdma_training
        self.adm_name = adm_name
        self.session_issos = []
        self.session_type = session_type
        self.history = []

        # Save to database based on adm_name.
        if self.adm_name.endswith("_db_"):
            self.adm_name = self.adm_name.removesuffix("_db_")
            self.save_to_database = True
        if self.session_type == 'eval':
            self.save_to_database = True
            self.ta1_integration = True
            max_scenarios = None

        self._add_history(
                "Start Session",
                {"Session ID": self.session_id,
                "ADM Name": self.adm_name,
                "Session Type": session_type},
                self.session_id)

        yaml_paths = []
        yaml_path = "swagger_server/itm/itm_scenario_configs/"
        if session_type == 'soartech' or session_type == 'eval':
            yaml_paths.append(yaml_path + 'soartech/')
        if session_type == 'adept' or session_type == 'eval':
            yaml_paths.append(yaml_path + 'adept/')
        self.number_of_scenarios = max_scenarios if max_scenarios else 1

        selected_yaml_directories = [
            f"{path}{folder}/"
            for path in yaml_paths
            for folder in self._get_sub_directory_names(path)]
        if max_scenarios != None and max_scenarios >= 1:
            # fill in extra scenarios with random copies
            inital_selected_yaml_directories = deepcopy(selected_yaml_directories)
            while len(selected_yaml_directories) < max_scenarios:
                random_directory = random.choice(inital_selected_yaml_directories)
                selected_yaml_directories.append(random_directory)
        else:
            max_scenarios = len(selected_yaml_directories)
        if session_type != 'eval':
            random.shuffle(selected_yaml_directories)
        for i in range(max_scenarios):
            scenario_object_handler = ITMSessionScenarioObjectHandler(yaml_path=selected_yaml_directories[i])
            itm_scenario_object = \
                scenario_object_handler.generate_session_scenario_object()
            self.session_issos.append(itm_scenario_object)
        self.current_isso_index = 0

        return self.session_id


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
                self._add_history(
                    "Tag Casualty",
                    {"Session ID": self.session_id, "Casualty ID": casualty.id, "Tag": tag},
                    self.scenario.state.to_dict())
                return

    def respond_to_tag_probe(self, action: Action):
        probe_id = None
        choice_id = None
        tag = action.parameters.get('category')
        if action.casualty_id == 'Mike':
            probe_id = 'adept-september-demo-probe-3'
            match tag:
                case 'MINIMAL':
                    choice_id = 's1-p3-choice1'
                case 'DELAYED':
                    choice_id = 's1-p3-choice2'
                case 'IMMEDIATE':
                    choice_id = 's1-p3-choice3'
                case 'EXPECTANT':
                    choice_id = 's1-p3-choice4'
        elif action.casualty_id == 'Civilian':
            probe_id = 'adept-september-demo-probe-4'
            match tag:
                case 'MINIMAL':
                    choice_id = 's1-p4-choice1'
                case 'DELAYED':
                    choice_id = 's1-p4-choice2'
                case 'IMMEDIATE':
                    choice_id = 's1-p4-choice3'
                case 'EXPECTANT':
                    choice_id = 's1-p4-choice4'

        if probe_id and choice_id:
            response = ProbeResponse(scenario_id=self.scenario.id, probe_id=probe_id, choice=choice_id, justification=action.justification)
            print(f"--> ADM action resulted in TA1 response with choice {response.choice}.")
            self.respond_to_probe(body=response)

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
                    time_passed = self.times_dict["SITREP"]
        else:
            # takes time for each responsive casualty during sitrep
            for curr_casualty in self.scenario.state.casualties:
                for isso_casualty in self.current_isso.scenario.state.casualties:
                    if isso_casualty.id == curr_casualty.id:
                        curr_casualty.vitals.mental_status = isso_casualty.vitals.mental_status
                        if curr_casualty.vitals.mental_status != "UNRESPONSIVE":
                            curr_casualty.vitals.conscious = isso_casualty.vitals.conscious
                            curr_casualty.vitals.breathing = isso_casualty.vitals.breathing
                            self._reveal_injuries(isso_casualty, casualty)
                            curr_casualty.visited = True
                        time_passed += self.times_dict["SITREP"]

        self._add_history(
            "Request SITREP", {"Session ID": self.session_id,
             "Casualty ID": casualty.id if casualty else "All casualties"},
            self.scenario.state.to_dict())

        return time_passed


    def respond_to_probe(self, body: ProbeResponse):
        """
        Respond to a probe from the probe system.

        Args:
            body: The probe response body as a dict.
        """
        body.justification = '' if body.justification == None else body.justification
        self.current_isso.probe_system.respond_to_probe(
            probe_id=body.probe_id,
            choice=body.choice,
            justification=body.justification
        )

        self._add_history(
            "Respond to TA1 Probe",
            {"Session ID": self.session_id, "Scenario ID": body.scenario_id, "Probe ID": body.probe_id,
             "Choice": body.choice, "Justification": body.justification},
            self.scenario.state.to_dict())

        if self.ta1_integration == True:
            self.current_isso.ta1_controller.post_probe(body)
            probe_response_alignment = \
                self.current_isso.ta1_controller.get_probe_response_alignment(
                body.scenario_id,
                body.probe_id
            )
            self._add_history(
                "TA1 Probe Response Alignment",
                {"Session ID": self.current_isso.ta1_controller.session_id,
                "Scenario ID": body.scenario_id,
                "Target ID": self.current_isso.ta1_controller.alignment_target_id,
                "Probe ID": body.probe_id},
                probe_response_alignment
            )
        else:
            print(f"--> Responding to probe {body.probe_id} from scenario {body.scenario_id} with choice {body.choice}.")

    def lookup_probe_response(self, action: Action) -> ProbeResponse:
        """
        Look up a probe response from the probe system based on the specified action

        Args:
            body: The probe response body as a dict.
        Returns:
            The probe corresponding to the action, or None if there is no corresponding probe.
        """

        if not action.action_id:
            return None

        if action.action_type == 'TAG_CASUALTY':
            return None # These are handled separately

        currentProbe = self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index]
        choice_id = None
        # need to go back through to find the choice from probeYamlOption (not stored in action)
        for option in currentProbe.options:
            if option.assoc_action["action_id"] == action.action_id:
                choice_id = option.ta1_id
                break

        return ProbeResponse(scenario_id=self.scenario.id, probe_id=currentProbe.id,
                             choice=choice_id, justification=action.justification) if choice_id != None else None


    def update_state(self, action: Action):
        # Update scenario state based on action
        # Note that by this time, the action has been fully validated

        # keeps track of time passed based on action taken (in seconds)
        time_passed = 0
        # Look up casualty action is applied to
        casualty = next((casualty for casualty in self.scenario.state.casualties if casualty.id == action.casualty_id), None)

        if action.action_type == "APPLY_TREATMENT":
            time_passed += self.apply_treatment(action, casualty)

        # if tagging a casualty then update the tag to the category parameter
        if action.action_type == "TAG_CASUALTY":
            self.tag_casualty(casualty, action.parameters.get('category'))
            time_passed += self.times_dict["TAG_CASUALTY"]
        
        if action.action_type == "CHECK_ALL_VITALS":
            self.check_all_vitals(casualty)
            time_passed += self.times_dict["CHECK_ALL_VITALS"]

        if action.action_type == "CHECK_PULSE":
            self.check_pulse(casualty)
            time_passed += self.times_dict["CHECK_PULSE"]

        if action.action_type == "CHECK_RESPIRATION":
            self.check_respiration(casualty)
            time_passed += self.times_dict["CHECK_RESPIRATION"]

        if action.action_type == "DIRECT_MOBILE_CASUALTIES":
            self._add_history(
                "Direct Mobile Casualties", {"Session ID": self.session_id},
                self.scenario.state.to_dict())
            time_passed += self.times_dict["DIRECT_MOBILE_CASUALTIES"]

        if action.action_type == "MOVE_TO_EVAC":
            self._add_history(
                "Move to EVAC", {"Session ID": self.session_id, "Casualty ID": casualty.id},
                self.scenario.state.to_dict())
            time_passed += self.times_dict["MOVE_TO_EVAC"]

        if action.action_type == "SITREP":
            time_passed += self.process_sitrep(casualty)

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
        self.scenario.state.elapsed_time += time_passed

    def take_action(self, body: Action) -> State:
        """
        Take an action within a scenario

        Args:
            body: Encapsulation of an action taken by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """

        # Validate that action is a valid, well-formed action
        (successful, message, code) = self._validate_action(body)
        if not successful:
            return message, code

        self._add_history(
            "Take Action",
            {"Session ID": self.session_id, "Scenario ID": self.scenario.id, "Action": body.to_dict()},
            self.scenario.state.to_dict())
        print(f"--> ADM chose action {body.action_type} with casualty {body.casualty_id} and parameters {body.parameters}.")

        # Only the ADM can end the scenario
        if body.action_type == 'END_SCENARIO':
            self._end_scenario()
            return self.scenario.state

        # Special handling for ADEPT tagging
        if self.scenario_rules == "ADEPT" and body.action_type == 'TAG_CASUALTY':
            self.respond_to_tag_probe(action=body)

        # Map action to probe response
        response = self.lookup_probe_response(action=body)

        # Actions with no corresponding probe could be constructed by ADM or pre-configured repeatable actions
        if response is None:
            self.update_state(action=body)
            return self.scenario.state

        # keep track of which casualty_id's have been addressed in this probe
        if not body.casualty_id in self.casualty_ids:
            self.casualty_ids.append(body.casualty_id)

        # remove option taken from being returned in get_available_actions
        if body.casualty_id:
            self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index].options = [
                option for option in self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index].options
                if option.assoc_action["action_id"] != body.action_id
            ]

        # Respond to probe with TA1
        # NOTE: Not all actions will necessarily result in a probe response
        # In the September scenarios, only the first action taken results in a response to a probe.
        if self.first_answer:
            print(f"--> ADM action resulted in TA1 response with choice {response.choice}.")
            self.respond_to_probe(body=response)
            self.first_answer = False

        # PROBE HANDLING FOR ADEPT
        if self.scenario_rules == "ADEPT":
            # move on to next probe when all casualty id's have at least one action towards them
            unanswered_casualty_id = False
            for option in self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index].options:
                if option.assoc_action.get("casualty_id") not in self.casualty_ids:
                    unanswered_casualty_id = True
                    break  # No need to continue checking once we find one unmatched id
            
            # Update scenario state
            self.update_state(action=body)
            if body.action_type == "MOVE_TO_EVAC":
                self.adept_evac_happened = True
            # if no unanswered casualties left, (or no options left)
            elif not unanswered_casualty_id or not self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index]:
                self.end_probe()
        else:
            # PROBE HANDLING FOR SOARTECH
            self.update_state(action=body)

        return self.scenario.state


    def end_probe(self):
        self.current_isso.probe_system.probe_count -= 1
        self.current_isso.probe_system.current_probe_index += 1
        self.scenario.state.scenario_complete = \
        self.current_isso.probe_system.probe_count <= 0
        # reset casualty_id list when going to next probe
        self.casualty_ids = []
        self.first_answer = True
        # Copy certain state from probe to scenario
        if not self.scenario.state.scenario_complete:
            newState :dict = self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index].state
            if newState.get("unstructured"):
                self.scenario.state.environment = newState.get("unstructured")
            if newState.get("environment"):
                self.scenario.state.environment = newState.get("environment")
            if newState.get("threat_state"):
                self.scenario.state.environment = newState.get("threat_state")


    def get_available_actions(self, scenario_id: str) -> List[Action]:
        """
        Take an action within a scenario

        Args:
            body: Encapsulation of an action taken by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """
        # Check for a valid scenario_id
        (successful, message, code) = self._check_scenario_id(scenario_id)
        if not successful:
            return message, code
        if self.scenario.session_complete:
            return 'Scenario Complete', 400

        actions: List[Action] = []
        if self.current_isso.probe_system.probe_yamls and not self.scenario.state.scenario_complete:
            if not self.adept_evac_happened:
                for option in self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index].options:
                    if (not self.kdma_training):
                        option.assoc_action.pop('kdma_association', None)
                    actions.append(option.assoc_action)
            if self.scenario_rules == 'SOARTECH' or self.adept_evac_happened:
                # Allow ADMs to end the scenario, usually
                actions.append(Action(action_id="end_scenario_action", action_type='END_SCENARIO', unstructured="End the scenario"))
            # Always allow tagging a casualty
            actions.append(Action(action_id="tag_action", action_type='TAG_CASUALTY', unstructured="Tag a casualty"))
        else:
             return 'Scenario Complete', 400

        return actions
