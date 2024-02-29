import time
import uuid
import random
import os
from typing import List
from copy import deepcopy
from swagger_server.models import (
    Action,
    AlignmentTarget,
    AlignmentResults,
    Scenario,
    State
)
from .itm_scenario import ITMScenario
from .itm_action_handler import ITMActionHandler
from .itm_history import ITMHistory

class ITMSession:
    """
    Class for representing and manipulating a simulation scenario session.
    """

    def __init__(self):
        """
        Initialize an ITMSession.
        """
        self.session_id = None
        self.adm_name = ''
        self.time_started = 0
        self.time_elapsed_realtime = 0

        self.session_type = ''
        self.using_max_scenarios = False
        self.kdma_training = False

        self.session_complete = False
        self.state: State = None
        self.current_scenario_index = 0
        self.itm_scenarios = []
        self.itm_scenario: ITMScenario = None

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
        if not scenario_id == self.itm_scenario.id:
            return False, f'Scenario ID {scenario_id} not found', 404
        return True, '', 0


    def end_scenario(self):
        """
        End the current scenario and store history to json file.
        """
        self.history.add_history(
            "Scenario ended", {"scenario_id": self.itm_scenario.id, "session_id": self.session_id,
                            "elapsed_time": self.state.elapsed_time}, None)
        print(f"--> Scenario '{self.itm_scenario.id}' ended.")
        self.state.scenario_complete = True

        if self.kdma_training:
            self.state.unstructured = 'Scenario complete.'
            self._cleanup()
            return

        session_alignment_score = None
        if self.ta1_integration:
            try:
                session_alignment :AlignmentResults = \
                    self.itm_scenario.ta1_controller.get_session_alignment()
                session_alignment_score = session_alignment.score
                self.history.add_history(
                    "TA1 Session Alignment",
                    {"session_id": self.itm_scenario.ta1_controller.session_id,
                    "target_id": self.itm_scenario.ta1_controller.alignment_target_id},
                    session_alignment.to_dict()
                )
                print(f"--> Got session alignment score {session_alignment_score} from TA1.")
            except:
                print("--> WARNING: Exception getting session alignment. Ignoring.")

        self.state.unstructured = f'Scenario {self.itm_scenario.id} complete. Session alignment score = {session_alignment_score}'
        self._cleanup()


    def _cleanup(self):
        if self.save_history:
            self.history.write_to_json_file()
        self.history.clear_history()


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
        if self.session_complete:
            return 'Scenario Complete', 400
        if self.kdma_training:
            return 'No alignment target in training sessions', 400
        return self.itm_scenario.alignment_target_reader.alignment_target

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
            self.state.to_dict())

        return self.state


    def start_scenario(self, scenario_id: str=None) -> Scenario:
        """
        Start a new scenario.

        Args:
            scenario_id: a scenario ID to start

        Returns:
            The started scenario as a Scenario object.
        """

        if scenario_id:
            if self.using_max_scenarios:
                return "Specifying a scenario ID is incompatible with /ta2/startSession's max_scenarios parameter.", 400
            index = 0
            self.itm_scenario = None
            for scenario in self.itm_scenarios:
                if scenario_id == scenario.id:
                    self.itm_scenario = scenario
                    self.current_scenario_index = index
                    break
                index += 1
            if self.itm_scenario is None:
                return f'Scenario ID `{scenario_id}` does not exist as {"a training" if self.kdma_training else "an eval"} scenario for `{self.session_type}`', 404
            if self.itm_scenario.isd.current_scene.state is None:
                return self._end_session() # We have already run the specified scenario to completion
        else:
            if self.state and not self.state.scenario_complete:
                return f'Must end `{self.itm_scenario.id}` before starting a new scenario', 400
            if self.current_scenario_index < len(self.itm_scenarios):
                self.itm_scenario = self.itm_scenarios[self.current_scenario_index]
            else:
                return self._end_session() # No more scenarios means we can end the session

        try:
            self.state = deepcopy(self.itm_scenario.isd.current_scene.state)
            ITMScenario.clear_hidden_data(self.state)
            scenario = Scenario(
                id=self.itm_scenario.id,
                name=self.itm_scenario.name,
                session_complete=False,
                state=self.state
            )
            self.action_handler.set_scenario(self.itm_scenario)
            self.current_scenario_index += 1

            self.history.add_history(
                "Start Scenario",
                {"session_id": self.session_id, "adm_name": self.adm_name},
                scenario.to_dict())
            print(f"--> Scenario '{self.itm_scenario.id}' starting.")

            if self.ta1_integration:
                try:
                    if not self.itm_scenario.ta1_controller.session_id \
                            or not self.kdma_training: # When training, allow TA1 sessions to span scenarios
                        ta1_session_id = self.itm_scenario.ta1_controller.new_session()
                        self.history.add_history(
                            "TA1 Session ID", {}, ta1_session_id
                        )
                        print(f"--> Got new session_id {ta1_session_id} from TA1.")
                    if not self.kdma_training:
                        scenario_alignment = self.itm_scenario.ta1_controller.get_alignment_target()
                        print(f"--> Got alignment target {scenario_alignment} from TA1.")
                        self.history.add_history(
                            "TA1 Alignment Target Data",
                            {"session_id": self.itm_scenario.ta1_controller.session_id,
                            "scenario_id": self.itm_scenario.id},
                            scenario_alignment
                        )
                except:
                    print("--> WARNING: Exception communicating with TA1; is the TA1 server running?  Ending session.")
                    self._end_session() # Exception here ends the session
                    return 'Exception communicating with TA1; is the TA1 server running?  Ending session.', 503
            else:
                if not self.kdma_training:
                    print("--> Got alignment target from TA1.")

            return scenario
        except:
            print("--> WARNING: Exception getting next scenario; ending session.")
            import traceback
            traceback.print_exc()
            return self._end_session() # Exception here ends the session

    def _end_session(self) -> Scenario:
        self.__init__()
        return Scenario(session_complete=True, id='', name='',
                        scenes=None, state=None)

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
        if self.session_id is None:
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
        self.itm_scenarios = []
        self.session_type = session_type
        self.history.clear_history()

        if self.session_type == 'eval':
            self.save_history = True
            self.ta1_integration = True
            max_scenarios = None
        elif kdma_training:
            self.ta1_integration = True

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

        selected_yaml_directories = [
            f"{path}{folder}/"
            for path in yaml_paths
            for folder in self._get_sub_directory_names(path)]
        if max_scenarios is not None and max_scenarios >= 1:
            self.using_max_scenarios = True
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
            itm_scenario = \
                ITMScenario(yaml_path=selected_yaml_directories[i],
                            session=self, training=self.kdma_training)
            itm_scenario.generate_scenario_data()
            self.itm_scenarios.append(itm_scenario)
        self.current_scenario_index = 0

        return self.session_id


    def take_action(self, body: Action) -> State:
        """
        Take an action within a scenario

        Args:
            body: Encapsulation of an action taken by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """

        message = f"--> ADM chose action {body.action_type}"
        if body.character_id:
            message += f" with character {body.character_id}"
            if body.parameters:
                message += f" and parameters {body.parameters}"
        elif body.parameters:
            message += f" with parameters {body.parameters}"
        print(message + '.')

        # Validate that action is a valid, well-formed action
        (successful, message, code) = self.action_handler.validate_action(body)
        if not successful:
            return message, code

        self.action_handler.process_action(action=body)
        return self.state


    def get_session_alignment(self, target_id: str) -> AlignmentResults:
        if not self.kdma_training:
            return 'Session alignment can only be requested during a training session', 403

        session_alignment :AlignmentResults = None
        if self.ta1_integration:
            try:
                if len(self.itm_scenario.probes_sent) > 0:
                    session_alignment = \
                        self.itm_scenario.ta1_controller.get_session_alignment(target_id=target_id)
                else:
                    session_alignment = AlignmentResults(alignment_source=[], alignment_target_id=target_id, score=0.5, kdma_values=[])

            except:
                print("--> WARNING: Exception getting session alignment.")
                return 'Could not get session alignment; is a TA1 server running?', 503
        else:
            session_alignment = AlignmentResults(alignment_source=[], alignment_target_id=target_id, score=0.5, kdma_values=[])
        print(f"--> Got session alignment score {session_alignment.score} from TA1 for alignment target id {target_id}.")
        return session_alignment


    def get_available_actions(self, scenario_id: str) -> List[Action]:
        """
        Take an action within a scenario

        Args:
            scenario_id: The ID of the scenario.

        Returns:
            A list of Actions that the DM can take.
        """
        # Check for a valid scenario_id
        (successful, message, code) = self._check_scenario_id(scenario_id)
        if not successful:
            return message, code
        if self.session_complete:
            return 'Scenario Complete', 400

        if  not self.state.scenario_complete:
            return self.itm_scenario.get_available_actions()
        else:
            return 'Scenario Complete', 400
