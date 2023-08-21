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
        self.session_type = 'test'
        self.current_isso: ITMSessionScenarioObject = None
        self.current_isso_index = 0
        self.session_issos = []
        self.number_of_scenarios = None
        self.scenario: Scenario = None

        self.probes_responded_to = []

        # This determines whether the server makes calls to TA1
        self.ta1_integration = False

        # This calls the dashboard's MongoDB
        self.save_to_database = False
        self.mongo_db = MongoDB('dashroot', 'dashr00tp@ssw0rd',
                                'localhost', '27017', 'dashboard')
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

        Raises:
            Exception: If the scenario ID does not match.
        """
        if not scenario_id == self.scenario.id:
            return False, 'Scenario ID not found', 404
        return True, '', 0


    def _check_session_id(self, session_id: str) -> None:
        """
        Check if the provided session ID matches the session's session ID.

        Args:
            session_id: The session ID to compare.

        Raises:
            Exception: If the session ID does not match.
        """
        if not session_id == self.session_id:
            return False, 'Invalid Session ID', 400
        return True, '', 0

    def _validate_action(self, action: Action) -> None:
        """
        Validate that action is a valid, well-formed action.

        Args:
            action: The action to validate.

        Raises:
            Exception: If the action is malformed.
        """
        # TODO ITM-74: Validate that action is well-formed
        if action is None:
            raise ValueError('Invalid or Malformed Action')
        
        if not action.scenario_id or not action.action_type or action.scenario_id == "" or action.action_type == "":
            raise ValueError('Invalid or Malformed Action: Missing scenario_id or action_type')
        
        if action.casualty_id and not isinstance(action.casualty_id, str):
            # if casualty id is not a str
            if not isinstance(action.casualty_id, str):
                raise ValueError('Invalid or Malformed Action: Invalid casualty_id')
            else:
                # see if casualty id of action actually maps to a casualty id in state
                casualty = next((casualty for casualty in self.scenario.state.casualties if casualty.id == action.casualty_id), None)
                if casualty is None:
                    raise ValueError('Casualty id not found in state')
                
        if action.unstructured and not isinstance(action.unstructured, str):
            raise ValueError('Invalid or Malformed Action: Invalid unstructured description')
        
        if action.justification and not isinstance(action.justification, str):
            raise ValueError('Invalid or Malformed Action: Invalid justification')
        
        if action.parameters:
            if not isinstance(action.parameters, list):
                raise ValueError('Invalid or Malformed Action: Parameters must be a list')
            for param in action.parameters:
                if not isinstance(param, dict) or any(key != 'str' or value != 'str' for key, value in param.items()):
                    raise ValueError('Invalid or Malformed Action: Invalid parameter format')
        
        return True, '', 0

    def _end_scenario(self):
        """
        End the current scenario and store history to mongo and json file.
        """
        if self.ta1_integration == True:
            alignment_target_session_alignment = \
                self.current_isso.ta1_controller.get_session_alignment()
            self._add_history(
                "TA1 Session Alignment",
                {"Session ID": self.current_isso.ta1_controller.session_id,
                "Target ID": self.current_isso.ta1_controller.alignment_target_id},
                alignment_target_session_alignment
            )
        if not self.save_to_database:
            self.history = []
            self.probes_responded_to = []
            return
        self.mongo_db.insert_data('scenarios', self.scenario.to_dict())
        insert_id = self.mongo_db.insert_data('test', {"history": self.history})
        retrieved_data = self.mongo_db.retrieve_data('test', insert_id)
        # Write the retrieved data to a local JSON file
        self.mongo_db.write_to_json_file(retrieved_data)
        self.history = []
        self.probes_responded_to = []


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


    def get_alignment_target(self, session_id: str, scenario_id: str) -> AlignmentTarget:
        """
        Get the alignment target for a specific scenario.

        Args:
            session_id: The ID of the session.
            scenario_id: The ID of the scenario.

        Returns:
            The alignment target for the specified scenario as an AlignmentTarget object.
        """

        # Check for a valid session_id and scenario_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code
        (successful, message, code) = self._check_scenario_id(scenario_id)
        if not successful:
            return message, code
        return self.current_isso.alignment_target_reader.alignment_target


    def get_heart_rate(self, session_id: str, casualty_id: str) -> int:
        """
        Get the heart rate of a casualty_id in the scenario.

        Args:
            session_id: The ID of the session.
            casualty_id: The ID of the casualty_id.

        Returns:
            The heart rate of the casualty as an integer.
        """

        # Check for a valid session_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code

        casualties: List[Casualty] = self.scenario.state.casualties
        for casualty in casualties:
            if casualty.id == casualty_id:
                response = casualty.vitals.hrpmin
                self._add_history(
                    "Get Heart Rate",
                    {"Session ID": self.session_id, "Casualty ID": casualty_id},
                    response)
                return response
        return 'Casualty ID not found', 404
    
    def get_respiration(self, session_id: str, casualty_id: str) -> int:
        """
        Get the heart rate of a casualty_id in the scenario.

        Args:
            session_id: The ID of the session.
            casualty_id: The ID of the casualty_id.

        Returns:
            The heart rate of the casualty as an integer.
        """

        # Check for a valid session_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code

        casualties: List[Casualty] = self.scenario.state.casualties
        for casualty in casualties:
            if casualty.id == casualty_id:
                response = casualty.vitals.breathing
                self._add_history(
                    "Get Respiration",
                    {"Session ID": self.session_id, "Casualty ID": casualty_id},
                    response)
                return response
        return 'Casualty ID not found', 404


    def get_scenario_state(self, session_id: str, scenario_id: str) -> State:
        """
        Get the current state of the scenario.

        Args:
            session_id: The ID of the session.
            scenario_id: The ID of the scenario.

        Returns:
            The current state of the scenario as a State object.
        """

        # Check for a valid session_id and scenario_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code
        (successful, message, code) = self._check_scenario_id(scenario_id)
        if not successful:
            return message, code

        self._add_history(
            "Get Scenario State",
            {"Session ID": self.session_id, "Scenario ID": scenario_id},
            self.scenario.state.to_dict())

        return self.scenario.state


    def get_vitals(self, session_id: str, casualty_id: str) -> Vitals:
        """
        Get the vitals of a casualty in the scenario.

        Args:
            session_id: The ID of the session.
            casualty_id: The ID of the casualty.

        Returns:
            The vitals of the casualty as a Vitals object.
        """

        # Check for a valid session_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code

        casualties: List[Casualty] = self.scenario.state.casualties
        for casualty in casualties:
            if casualty.id == casualty_id:
                response = casualty.vitals.to_dict()
                self._add_history(
                    "Get Vitals",
                    {"Session ID": self.session_id, "Casualty ID": casualty_id},
                    response)
                return casualty.vitals
        return 'Casualty ID not found', 404


    def start_scenario(self, session_id: str, scenario_id: str=None) -> Scenario:
        """
        Start a new scenario.

        Args:
            session_id: The ID of the session.
            scenario_id: a scenario ID to start, used internally by TA3

        Returns:
            The started scenario as a Scenario object.
        """

        # Check for a valid session_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code

        # TODO this needs to get a specific scenario by id
        if scenario_id:
            raise connexion.ProblemException(status=403, title="Forbidden", detail="Sorry, internal TA3 only")
        
        # TODO this needs to check if we don't have this scenario id
        if scenario_id and not scenario_id not in ['scenario_id_list']:
            return "Scenario ID does not exist", 404
        
        # placeholder for System Overload error code
        system_overload = False
        if system_overload:
            return "System Overload", 418

        try:
            self.current_isso: ITMSessionScenarioObject = self.session_issos[self.current_isso_index]
            self.scenario = self.current_isso.scenario
            self.current_isso_index += 1

            self._add_history(
                "Start Scenario",
                {"Session ID": self.session_id},
                self.scenario.to_dict())

            if self.ta1_integration == True:
                ta1_session_id = self.current_isso.ta1_controller.new_session()
                self._add_history(
                    "TA1 Alignment Target Session ID", {}, ta1_session_id
                )
                scenario_alignment = self.current_isso.ta1_controller.get_alignment_target()
                self._add_history(
                    "TA1 Alignment Target Data",
                    {"Session ID": self.current_isso.ta1_controller.session_id,
                    "Scenario ID": self.current_isso.scenario.id},
                    scenario_alignment
                )

            return self.scenario
        except:
            # Empty Scenario means we can end the session
            self.__init__()
            return Scenario(session_complete=True, id='', name='',
                            start_time=None, state=None, triage_categories=None)


    def start_session(self, adm_name: str, session_type: str, max_scenarios=None) -> str:
        """
        Start a new session.

        Args:
            adm_name: The adm name associated with the scenario.
            session_type: The type of scenarios either soartech, adept, test, or eval
            max_scenarios: The max number of scenarios presented during the session

        Returns:
            A new session Id to use in subsequent calls
        """
        if session_type not in ['test', 'adept', 'soartech', 'eval']:
            return (
                'Invalid session type. Must be "test, adept, soartech, or eval"',
                400
            )

        # For now, send System Overload error code if a session is already being processed
        if self.session_id == None:
            self.session_id = str(uuid.uuid4())
        else:
            return 'System Overload', 418

        self.adm_name = adm_name
        self.session_issos = []
        self.session_type = session_type
        self.history = []
        self.probes_responded_to = []

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
        if session_type == 'soartech' or session_type == 'test' or session_type == 'eval':
            yaml_paths.append(yaml_path + 'soartech/')
        if session_type == 'adept' or session_type == 'test' or session_type == 'eval':
            yaml_paths.append(yaml_path + 'adept/')
        self.number_of_scenarios = max_scenarios

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
        random.shuffle(selected_yaml_directories)
        for i in range(max_scenarios):
            scenario_object_handler = ITMSessionScenarioObjectHandler(yaml_path=selected_yaml_directories[i])
            itm_scenario_object = \
                scenario_object_handler.generate_session_scenario_object()
            self.session_issos.append(itm_scenario_object)
        self.current_isso_index = 0

        return self.session_id


    def tag_casualty(self, session_id: str, casualty_id: str, tag: str) -> str:
        """
        Tag a casualty with a triage category

        Args:
            session_id: The ID of the session.
            casualty_id: The ID of the casualty.
            tag: The tag to assign to the casualty.

        Returns:
            The current state of the scenario as a State object.
        """

        # Check for a valid session_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code

        for casualty in self.scenario.state.casualties:
            if casualty.id == casualty_id:
                casualty.tag = tag
                response = self.scenario.state
                self._add_history(
                    "Tag Casualty",
                    {"Session ID": self.session_id, "Casualty ID": casualty_id, "Tag": tag},
                    response.to_dict())
                return response
        return 'Casualty ID not found', 404

    def respond_to_probe(self, body: ProbeResponse):
        """
        Respond to a probe from the probe system.

        Args:
            body: The probe response body as a dict.
        """
        self.probes_responded_to.append(body.probe_id)
        body.justification = '' if body.justification == None else body.justification
        self.current_isso.probe_system.generate_probe(self.scenario.state)
        self.current_isso.probe_system.respond_to_probe(
            probe_id=body.probe_id,
            choice=body.choice,
            justification=body.justification
        )

        self.current_isso.probe_system.probe_count -= 1
        self.current_isso.probe_system.current_probe_index += 1
        self.scenario.state.scenario_complete = \
            self.current_isso.probe_system.probe_count <= 0

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

    def lookup_probe_response(self, action: Action) -> ProbeResponse:
        """
        Look up a probe response from the probe system based on the specified action

        Args:
            body: The probe response body as a dict.
        """

        # TODO ITM-75: Map ADM action back to a TA1 probe response
        return ProbeResponse(scenario_id=action.scenario_id, probe_id="september-demo-probe-1", choice="choice1")


    def update_state(self, action: Action):
        # TODO ITM-69: Update scenario state based on action
        # keeps track of time passed based on action taken (in seconds)
        time_passed = 0
        # Look up casualty action is applied to
        casualty = next((casualty for casualty in self.scenario.state.casualties if casualty.id == action.casualty_id), None)
        # Check we have a reference to the casualty
        if action.action_type == "APPLY_TREATMENT":
            # load in time (in seconds) each treatment type takes
            with open("treatment_times_config/example.json", 'r') as json_file:
                treatment_times_dict = json.load(json_file)
            # using getattr in case treatment not provided as parameter
            supplies_used = getattr(action.parameters, 'treatment', None)
            for supply in self.scenario.state.supplies:
                if supply.type == supplies_used:
                    # removing one instance of the supplies_used e.g Tourniquet from supplies list
                    supply.quantity -= 1
                    if supplies_used in treatment_times_dict:
                        # increment time passed during treatment
                        time_passed += treatment_times_dict[supplies_used]
            
            # remove injury from casualty
            for injury in casualty.injuries:
                if injury.location == action.parameters.location:
                    casualty.remove(injury)
                    break
        
        # if tagging a casualty then update the tag to the category parameter
        if action.action_type == "TAG_CASUALTY":
            # getattr to account for partially specified action. If they don't tell us what to change the tag to keep it the same
            tag = getattr(action.parameters, 'category', casualty.tag)
            self.tag_casualty(self.session_id, casualty.id, tag)
            time_passed += 10
        
        # I don't think updating vitals does anything here because the get_vitals and get heart rate funcs 
        # just return what is already in the casualties vitals field. Probably not needed but was included in ticket
        if action.action_type == "CHECK_ALL_VITALS":
            vitals = self.get_vitals(self.session_id, casualty.id)
            casualty.vitals = vitals
            time_passed += 20

        if action.action_type == "CHECK_PULSE":
            casualty.vitals.hrpmin = self.get_heart_rate(self.session_id, casualty.id)
            time_passed += 10

        if action.action_type == "CHECK_RESPIRATION":
            casualty.vitals.breathing = self.get_respiration(self.session_id, casualty.id)
            time_passed += 10

        if action.action_type == "DIRECT_MOBILE_CASUALTIES":
            time_passed += 10

        if action.action_type == "SITREP":
            # takes 10 seconds for each responsive casualty during sitrep
            for curr_casualty in self.scenario.state.casualties:
                if curr_casualty.vitals.responsive:
                    time_passed += 10
    
        # For now, any action does nothing but ends the scenario!
        # self.scenario.state.scenario_complete = True

        # TODO ITM-72: Enhance casualty deterioration/amelioration
        # Ultimately, this should update values based DIRECTLY on how the sim does it
        time_elapsed_during_treatment = self.current_isso.casualty_simulator.treat_casualty(
            casualty_id=action.casualty_id,
            supply=action.justification
        )

        # TODO ITM-70: Add hard-coded elapsed time model, and update in state
        # Bonus: make it externally configurable
        self.time_elapsed_scenario_time += time_elapsed_during_treatment + time_passed
        self.current_isso.casualty_simulator.update_vitals(time_elapsed_during_treatment)
        self.scenario.state.elapsed_time = self.time_elapsed_scenario_time


    def take_action(self, session_id: str, body: Action) -> State:
        """
        Take an action within a scenario

        Args:
            session_id: The ID of the session.
            body: Encapsulation of an action taken by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """

        # Check for a valid session_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code

        # Validate that action is a valid, well-formed action
        (successful, message, code) = self._validate_action(body)
        if not successful:
            return message, code

        # Map action to probe response
        response = self.lookup_probe_response(action=body)

        # Respond to probe with TA1
        # NOTE: Not all actions will necessarily result in a probe response
        #self.respond_to_probe(body=response)

        # Update scenario state
        self.update_state(action=body)

        self._add_history(
            "Take Action",
            {"Session ID": self.session_id, "Scenario ID": self.scenario.id, "Action": body},
            self.scenario.state.to_dict())

        return self.scenario.state


    def get_available_actions(self, session_id: str, scenario_id: str) -> List[Action]:
        """
        Take an action within a scenario

        Args:
            session_id: The ID of the session.
            body: Encapsulation of an action taken by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """

        # Check for a valid session_id and scenario_id
        (successful, message, code) = self._check_session_id(session_id)
        if not successful:
            return message, code
        (successful, message, code) = self._check_scenario_id(scenario_id)
        if not successful:
            return message, code

        # TODO ITM-71: Add "training mode" that returns KDMA associations
        # TODO ITM-67: Return a list of available actions based on associated actions in scenario/probe configuration
        actions: List[Action] = []
        # read probe from yaml requires path to the yaml file leaving blank for now
        probeYamlList = self.current_isso.probe_system.read_all_probes_yamls_for_scenario()
        for probeYaml in probeYamlList:
            for option in probeYaml.options:
                actions.append(option.assoc_action)

        return actions
