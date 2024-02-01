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
    InjuryStatusEnum,
    Scenario,
    State,
    Vitals
)
from swagger_server.models.probe_response import ProbeResponse
from .itm_scenario import ITMScenario
from .itm_action_handler import ITMActionHandler
from .itm_history import ITMHistory
from .itm_ta1_controller import ITMTa1Controller

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
        self.number_of_scenarios = None
        self.custom_scenario_count = 0 # when scenario_id is specified in start_scenario
        self.ta1_controller: ITMTa1Controller = None

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

    def _end_scenario(self):
        """
        End the current scenario and store history to json file.

        Returns:
            The session alignment from TA1.
        """
        self.state.scenario_complete = True
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
        for character in self.state.characters:
            character.injuries[:] = \
                [injury for injury in character.injuries if injury.status == InjuryStatusEnum.VISIBLE]
            character.unstructured_postassess = None
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
            self.itm_scenario = None
            for scenario in self.itm_scenarios:
                if scenario_id == scenario.id:
                    self.itm_scenario = scenario
                    self.current_scenario_index = index
                    self.custom_scenario_count += 1
                    break
                index += 1
            if self.itm_scenario is None:
                return f'Scenario ID `{scenario_id}` does not exist for `{self.session_type}`', 404
        else:
            # Require ADM to end the scenario explicitly
            if self.state and not self.state.scenario_complete:
                return f'Must end `{self.itm_scenario.id}` before starting a new scenario', 400
            if self.current_scenario_index < len(self.itm_scenarios):
                self.itm_scenario = self.itm_scenarios[self.current_scenario_index]
            else:
                return self._end_session() # No more scenarios means we can end the session

        try:
            self.state = deepcopy(self.itm_scenario.isd.scenario.state)
            scenario = Scenario(
                id=self.itm_scenario.id,
                name=self.itm_scenario.isd.scenario.name,
                session_complete=False,
                state=self.state
            )
            self._clear_hidden_data()
            self.action_handler.set_scenario(self.itm_scenario)
            self.current_scenario_index += 1

            self.history.add_history(
                "Start Scenario",
                {"session_id": self.session_id, "adm_name": self.adm_name},
                scenario.to_dict())

            if self.ta1_integration:
                self.ta1_controller = self.itm_scenario.ta1_controller
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
                        "scenario_id": self.itm_scenario.id},
                        scenario_alignment
                )
            else:
                # TODO: consider different/better way to disable TA1 communcation from ITMScenario
                self.itm_scenario.ta1_controller = None
                if not self.kdma_training:
                    print("--> Got alignment target from TA1.")

            return scenario
        except:
            print("--> Exception getting next scenario; ending session.")
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
        self.itm_scenarios = []
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
            itm_scenario = \
                ITMScenario(yaml_path=selected_yaml_directories[i],
                                                training=self.kdma_training)
            itm_scenario.generate_scenario_data()
            self.itm_scenarios.append(itm_scenario)
        self.current_scenario_index = 0

        return self.session_id


    # TODO: Move to ITMScenario or ITMScene
    def respond_to_probe(self, body: ProbeResponse):
        """
        Respond to a probe from the probe system.

        Args:
            body: The probe response body as a dict.
        """
        body.justification = '' if body.justification == None else body.justification

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

        # Only the ADM can end the scene
        if body.action_type == 'END_SCENE':
            self.history.add_history(
                "Take Action", {"action_type": body.action_type, "session_id": self.session_id,
                                "elapsed_time": self.state.elapsed_time}, None)
            session_alignment_score = self._end_scenario()
            if self.kdma_training:
                self.state.unstructured = f'Scenario {self.itm_scenario.id} complete. Session alignment score = {session_alignment_score}'
            else:
                self.state.unstructured = 'Scenario complete.'
            return self.state

        self.action_handler.process_action(action=body)
        return self.state


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

        if self.itm_scenario.isd.scenario and not self.state.scenario_complete:
            return self.itm_scenario.get_available_actions()
        else:
            return 'Scenario Complete', 400