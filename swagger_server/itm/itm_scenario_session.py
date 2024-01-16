import time
import uuid
import random
import os
import connexion
from typing import List
from copy import deepcopy
from swagger_server.models import (
    Action,
    AlignmentTarget,
    AlignmentResults,
    Scenario,
    State,
    Vitals
)
from swagger_server.models.probe_response import ProbeResponse
from .itm_session_scenario_object import (
    ITMSessionScenarioObjectHandler,
    ITMSessionScenarioObject
)
from .itm_action_handler import ITMActionHandler
from .itm_history import ITMHistory
from .itm_ta1_controller import ITMTa1Controller

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

        # isso is short for ITM Session Scenario Object
        self.session_type = ''
        self.current_isso: ITMSessionScenarioObject = None
        self.current_isso_index = 0
        self.session_issos = []
        self.number_of_scenarios = None
        self.custom_scenario_count = 0 # when scenario_id is specified in start_scenario
        self.scenario: Scenario = None
        self.first_answer: bool = True
        self.ta1_controllers = {}
        self.ta1_controller: ITMTa1Controller = None

        # hacky stuff for adept
        self.character_ids = []
        self.adept_evac_happened = False
        # adept or ST
        self.scenario_rules = ""

        # Action Handler
        self.action_handler: ITMActionHandler = ITMActionHandler(self)
        # ADM History
        self.history: ITMHistory = ITMHistory()
        # This determines whether the server makes calls to TA1
        self.ta1_integration = False
        # This determines whether the server saves history to JSON
        self.save_history = False


    def _check_scenario_id(self, scenario_id: str) -> None:
        """
        Check if the provided scenario ID matches the session's scenario ID.

        Args:
            scenario_id: The scenario ID to compare.
        """
        if not scenario_id == self.scenario.id:
            return False, f'Scenario ID {scenario_id} not found', 404
        return True, '', 0

    def _end_scenario(self):
        """
        End the current scenario and store history to json file.

        Returns:
            The session alignment from TA1.
        """
        self.scenario.state.scenario_complete = True
        self.adept_evac_happened = False
        self.first_answer = True
        session_alignment_score = 0.0

        if self.ta1_integration == True:
            session_alignment :AlignmentResults = \
                self.ta1_controller.get_session_alignment()
            session_alignment_score = session_alignment.score
            self.history.add_history(
                "TA1 Session Alignment",
                {"session_id": self.ta1_controller.session_id,
                "target_id": self.ta1_controller.alignment_target_id},
                session_alignment.to_dict()
            )
        print(f"--> Got session alignment score {session_alignment_score} from TA1.")

        if self.save_history:
            self.history.write_to_json_file()

        self.history.clear_history()
        return session_alignment_score


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

    # Hide vitals and hidden injuries at start of scenario
    def _clear_hidden_data(self):
        for character in self.scenario.state.characters:
            character.injuries[:] = \
                [injury for injury in character.injuries if injury.name not in self.current_isso.hidden_injury_types]
            character.vitals = Vitals()


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
        if self.kdma_training:
            return 'No alignment target in training sessions', 400
        return self.current_isso.alignment_target_reader.alignment_target

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

        self.history.add_history(
            "Get Scenario State",
            {"session_id": self.session_id, "scenario_id": scenario_id},
            self.scenario.state.to_dict())

        return self.scenario.state


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
            # Require ADM to end the scenario explicitly
            if self.scenario and self.scenario.state and not self.scenario.state.scenario_complete:
                return f'Must end `{self.scenario.id}` before starting a new scenario', 400
            if self.current_isso_index < len(self.session_issos):
                self.current_isso: ITMSessionScenarioObject = self.session_issos[self.current_isso_index]
            else:
                return self._end_session() # No more scenarios means we can end the session

        try:
            self.scenario = deepcopy(self.current_isso.scenario)
            self._clear_hidden_data()
            self.action_handler.set_isso(self.current_isso)
            self.current_isso_index += 1

            # the rules are different... so we need to know which group the scenario is from
            if self.scenario.id.__contains__("adept"):
                self.scenario_rules = "ADEPT"
            else:
                self.scenario_rules = "SOARTECH"

            self.history.add_history(
                "Start Scenario",
                {"session_id": self.session_id, "adm_name": self.adm_name},
                self.scenario.to_dict())

            if self.ta1_integration:
                self.ta1_controller = self.ta1_controllers[self.scenario_rules.lower()]
                if not self.ta1_controller.session_id \
                        or not self.kdma_training: # When training, allow TA1 sessions to span scenarios
                    ta1_session_id = self.ta1_controller.new_session()
                    self.history.add_history(
                        "TA1 Session ID", {}, ta1_session_id
                    )
                    print(f"--> Got new session_id {ta1_session_id} from TA1.")
                if not self.kdma_training:
                    scenario_alignment = self.ta1_controller.get_alignment_target()
                    print(f"--> Got alignment target {scenario_alignment} from TA1.")
                    self.history.add_history(
                        "TA1 Alignment Target Data",
                        {"session_id": self.ta1_controller.session_id,
                        "scenario_id": self.current_isso.scenario.id},
                        scenario_alignment
                )
            elif not self.kdma_training:
                print("--> Got alignment target from TA1.")

            return self.scenario
        except:
            print("--> Exception getting next scenario; ending session.")
            import traceback
            traceback.print_exc()
            return self._end_session() # Exception here ends the session

    def _end_session(self) -> Scenario:
        self.__init__()
        return Scenario(session_complete=True, id='', name='',
                        start_time=None, state=None)

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
            self.history.add_history(
                "Abort Session", {"session_id": self.session_id, "adm_name": self.adm_name}, None)
            self.__init__()
            self.session_id = str(uuid.uuid4()) # but assign new session_id for clarity in logs/history
        else:
            return 'System Overload', 503 # itm_ta2_eval_controller should prevent this

        self.kdma_training = kdma_training
        self.adm_name = adm_name
        self.session_issos = []
        self.session_type = session_type
        self.history.clear_history()

        if self.session_type == 'eval':
            self.save_history = True
            self.ta1_integration = True
            max_scenarios = None

        self.history.add_history(
                "Start Session",
                {"session_id": self.session_id,
                "adm_name": self.adm_name,
                "session_type": session_type},
                self.session_id)

        yaml_paths = []
        yaml_path = "swagger_server/itm/itm_" + ("training_scenarios/" if self.kdma_training else "eval_scenarios/")
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
            scenario_object_handler = \
                ITMSessionScenarioObjectHandler(yaml_path=selected_yaml_directories[i],
                                                training=self.kdma_training)
            itm_scenario_object = \
                scenario_object_handler.generate_session_scenario_object()
            self.session_issos.append(itm_scenario_object)
            self.ta1_controllers[scenario_object_handler.scene_type] = itm_scenario_object.ta1_controller
        self.current_isso_index = 0

        return self.session_id


    def respond_to_tag_probe(self, action: Action):
        probe_id = None
        choice_id = None
        tag = action.parameters.get('category')
        if action.character_id == 'Mike':
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
        elif action.character_id == 'Civilian':
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

        self.history.add_history(
            "Respond to TA1 Probe",
            {"session_id": self.session_id, "scenario_id": body.scenario_id, "probe_id": body.probe_id,
             "choice": body.choice, "justification": body.justification},
             None
            )

        if self.ta1_integration == True:
            self.ta1_controller.post_probe(body)
            probe_response_alignment = \
                self.ta1_controller.get_probe_response_alignment(
                body.scenario_id,
                body.probe_id
            )
            self.history.add_history(
                "TA1 Probe Response Alignment",
                {"session_id": self.ta1_controller.session_id,
                "scenario_id": body.scenario_id,
                "target_id": self.ta1_controller.alignment_target_id,
                "probe_id": body.probe_id},
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

        if action.action_type == 'TAG_CHARACTER':
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


    def take_action(self, body: Action) -> State:
        """
        Take an action within a scenario

        Args:
            body: Encapsulation of an action taken by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """

        # Validate that action is a valid, well-formed action
        (successful, message, code) = self.action_handler.validate_action(body)
        if not successful:
            return message, code

        print(f"--> ADM chose action {body.action_type} with character {body.character_id} and parameters {body.parameters}.")

        # Only the ADM can end the scenario
        if body.action_type == 'END_SCENARIO':
            self.history.add_history(
                "Take Action", {"action_type": body.action_type, "session_id": self.session_id,
                                "elapsed_time": self.scenario.state.elapsed_time}, None)
            session_alignment_score = self._end_scenario()
            if self.kdma_training:
                self.scenario.state.unstructured = f'Scenario {self.scenario.id} complete. Session alignment score = {session_alignment_score}'
            else:
                self.scenario.state.unstructured = 'Scenario complete.'
            return self.scenario.state

        # Special handling for ADEPT tagging
        if self.scenario_rules == "ADEPT" and body.action_type == 'TAG_CHARACTER':
            self.respond_to_tag_probe(action=body)

        # Map action to probe response
        response = self.lookup_probe_response(action=body)

        # Actions with no corresponding probe could be constructed by ADM or pre-configured repeatable actions
        if response is None:
            self.action_handler.process_action(action=body)
            return self.scenario.state

        # Keep track of which character_id's have been addressed in this probe
        if not body.character_id in self.character_ids:
            self.character_ids.append(body.character_id)

        # Remove option taken from being returned in get_available_actions
        # NOTE: this code currently keys off of the action having a character_id to determine if we remove the action
        # from the list of available actions.  This behavior is specific to the September milestone and will have to
        # be revisited/revised.
        if body.character_id:
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
            # Move on to next probe when all character id's have at least one action towards them
            unanswered_character_id = False
            for option in self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index].options:
                if option.assoc_action.get("character_id") not in self.character_ids:
                    unanswered_character_id = True
                    break  # No need to continue checking once we find one unmatched id
            
            # Update scenario state
            self.action_handler.process_action(action=body)
            if body.action_type == "MOVE_TO_EVAC":
                self.adept_evac_happened = True
            # if no unanswered characters left, (or no options left)
            elif not unanswered_character_id or not self.current_isso.probe_system.probe_yamls[self.current_isso.probe_system.current_probe_index]:
                self.end_probe()
        else:
            # PROBE HANDLING FOR SOARTECH
            self.action_handler.process_action(action=body)

        return self.scenario.state


    def end_probe(self):
        self.current_isso.probe_system.probe_count -= 1
        self.current_isso.probe_system.current_probe_index += 1
        self.scenario.state.scenario_complete = \
        self.current_isso.probe_system.probe_count <= 0
        # reset character_id list when going to next probe
        self.character_ids = []
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


    def get_session_alignment(self, target_id: str) -> AlignmentResults:
        if not self.kdma_training:
            return 'Session alignment can only be requested during a training session', 403

        session_alignment :AlignmentResults = None
        if self.ta1_integration == True:
            session_alignment = \
                self.ta1_controller.get_session_alignment(target_id=target_id)
        else:
            session_alignment = AlignmentResults(None, target_id, 0.0, None)
        print(f"--> Got session alignment score {session_alignment.score} from TA1 for alignment target id {target_id}.")
        return session_alignment


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
            # Always allow tagging a character
            actions.append(Action(action_id="tag_action", action_type='TAG_CHARACTER', unstructured="Tag a character"))
        else:
             return 'Scenario Complete', 400

        return actions
