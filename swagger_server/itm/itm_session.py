import time
import uuid
import random
import os
import logging
from datetime import datetime
from typing import List
from copy import deepcopy
from json import dumps
from swagger_server.models import (
    Action,
    AlignmentTarget,
    AlignmentResults,
    Scenario,
    State
)
from .itm_scenario import ITMScenario
from .itm_action_handler import ITMActionHandler
from .itm_alignment_target_reader import ITMAlignmentTargetReader
from .itm_ta1_controller import ITMTa1Controller
from .itm_history import ITMHistory

class ITMSession:
    """
    Class for representing and manipulating a simulation scenario session.
    """
    # Class variables
    EVALUATION_TYPE = 'metrics'
    local_alignment_targets = {} # alignment_targets baked into server, for use when not connecting to TA1
    alignment_data = {} # maps ta1_name to list alignment_targets, used whether connecting to TA1 or not
    ta1_controllers = {} # map of ta1_names to lists of ta1_controllers
    ta1_connected = False # have we successfully connected to TA1?

    def __init__(self):
        """
        Initialize an ITMSession.
        """
        self.session_id = None
        self.adm_name = ''
        self.adm_profile = ''
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
        self.ta1_integration = False # Default here applies to non-training, non-eval sessions
        # This determines whether the server returns history in final State after each scenario completes
        self.return_scenario_history = False
        # This determines whether the server saves history to JSON
        self.save_history = False
        # save_history must also be True
        self.save_history_to_s3 = False

    def __deepcopy__(self, memo):
        return self # Allows us to deepcopy ITMScenarios

    @staticmethod
    def initialize():
        logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s', datefmt='%m-%d %I:%M:%S')
        ta1_names = ITMSession.init_local_data()
        logging.info("Loaded local alignment targets from configuration.")
        try:
            logging.info("Loading TA1 configuration from TA1 servers...")
            ITMSession.init_ta1_data(ta1_names)
            ITMSession.ta1_connected = True
            logging.info("Done.")
        except:
            logging.warning("Could not initialize TA1 data. Running standalone with local alignment targets.")

        # If we couldn't use data from TA1, initialize with local data.
        if not ITMSession.ta1_connected:
            for ta1_name in ta1_names:
                ITMSession.alignment_data[ta1_name] = ITMSession.local_alignment_targets[ta1_name]


    @staticmethod
    def init_local_data():
        path = f"swagger_server/itm/data/{ITMSession.EVALUATION_TYPE}/local_alignment_targets/"
        ta1_names = ITMSession._get_sub_directory_names(path)
        for ta1_name in ta1_names:
            targets = ITMSession._get_file_names(path + ta1_name)
            ITMSession.local_alignment_targets[ta1_name] = []
            for target in targets:
                target_reader = ITMAlignmentTargetReader(f"{path}{ta1_name}/{target}")
                ITMSession.local_alignment_targets[ta1_name].append(target_reader.alignment_target)
        return ta1_names


    @staticmethod
    def init_ta1_data(ta1_names):
        # Populate alignment_data from ITMTa1Controller.get_alignment_data
        # Populate ta1_controllers from alignment_data
        for ta1_name in ta1_names:
            ITMSession.alignment_data[ta1_name] = [
                alignment_target for alignment_target in ITMTa1Controller.get_alignment_data(ta1_name)
                    if 'train' not in alignment_target.id
            ]
            ITMSession.ta1_controllers[ta1_name] = [
                ITMTa1Controller(alignment_target_id=alignment_target.id,
                                 scene_type=ta1_name,
                                 alignment_target=alignment_target)
                                 for alignment_target in ITMSession.alignment_data[ta1_name]
                                 ]


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
        logging.info("Scenario %s ended.", self.itm_scenario.id)
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
                self.itm_scenario.id(f"Got session alignment score %s from TA1.", session_alignment_score)
                alignment_scenario_id = session_alignment.alignment_source[0].scenario_id
                if self.itm_scenario.id != alignment_scenario_id:
                    logging.error("\033[92mContamination in session_alignment! scenario is %s but alignment source scenario is %s.\033[00m",
                                    self.itm_scenario.id, alignment_scenario_id)
            except Exception:
                logging.exception("Exception getting session alignment. Ignoring.")

        self.state.unstructured = f'Scenario {self.itm_scenario.id} complete. Session alignment score = {session_alignment_score}'
        self._cleanup()


    def _cleanup(self):
        if self.save_history:
            alignment_type = 'high' if 'high' in self.itm_scenario.alignment_target.id.lower() else 'low'
            timestamp = f"{datetime.now():%b%d-%H.%M.%S}" # e.g., "jungle-1-soartech-high-Mar13-11.44.44"
            filename = f"{self.itm_scenario.id.replace(' ', '_')}-{self.itm_scenario.scene_type}-{alignment_type}-{timestamp}"
            self.history.write_to_json_file(filename, self.save_history_to_s3)
        if self.return_scenario_history:
            self.state.unstructured = dumps({'history': self.history.history}, indent=2) + os.linesep + self.state.unstructured
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


    @staticmethod
    def _contains_filters(filespec, filters):
        for filter in filters:
            if filter not in filespec:
                return False
        return True

    @staticmethod
    def _get_file_names(directory, filters = [""]):
        """
        Return the filespec of all of the files inside of the
        specified directory.

        Args:
            directory: The directory to search inside of for files.
            filters: optional list of substrings to filter results
        """

        filespecs = []
        full_list = os.listdir(directory)
        filtered_list = [
            filespec for filespec in full_list if ITMSession._contains_filters(filespec, filters)
        ]
        for item in filtered_list:
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                filespecs.append(item)
        return filespecs

    @staticmethod
    def _get_sub_directory_names(directory):
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

        if self.session_type == 'eval' and 'base' in self.adm_profile:
            logging.warning('\033[92mAn ADM with "base" in the ADM profile is requesting an alignment target during evaluation.\033[00m')

        return self.itm_scenario.alignment_target

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
                {"session_id": self.session_id, "adm_name": self.adm_name, "adm_profile" : self.adm_profile},
                scenario.to_dict())
            logging.info("Scenario %s starting.", self.itm_scenario.id)

            if self.ta1_integration:
                try:
                    ta1_session_id = self.itm_scenario.ta1_controller.new_session()
                    self.history.add_history(
                        "TA1 Session ID", {}, ta1_session_id
                    )
                    logging.info("Got new session_id from TA1.", ta1_session_id)
                except:
                    logging.exception("Exception communicating with TA1; is the TA1 server running?  Ending session.")
                    self._end_session() # Exception here ends the session
                    return 'Exception communicating with TA1; is the TA1 server running?  Ending session.', 503

            # Get alignment target; was previously obtained either from TA1 or from local configuration.
            if not self.kdma_training:
                alignment_target = self.itm_scenario.alignment_target
                logging.info("Using alignment target %s.", alignment_target)
                self.history.add_history(
                    "Alignment Target",
                    {"session_id": self.itm_scenario.ta1_controller.session_id if self.ta1_integration else None,
                    "scenario_id": self.itm_scenario.id},
                    alignment_target.to_dict()
                )

            return scenario
        except:
            logging.exception("Exception getting next scenario; ending session.")
            self._end_session() # Exception here ends the session
            return 'Exception getting next scenario; ending session.', 503

    def _end_session(self) -> Scenario:
        self.__init__()
        return Scenario(session_complete=True, id='', name='',
                        scenes=None, state=None)

    def start_session(self, adm_name: str, session_type: str, adm_profile: str, kdma_training: bool, max_scenarios=None) -> str:
        """
        Start a new session.

        Args:
            adm_name: The ADM name associated with the session.
            session_type: The type of scenarios either soartech, adept, or eval
            adm_profile: a profile of the ADM in terms of its alignment strategy
            kdma_training: whether or not this is a training session with TA2
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
            logging.info("Re-using session %s for ADM %s", self.session_id, self.adm_name)
            self.history.add_history(
                "Abort Session", {"session_id": self.session_id, "adm_name": self.adm_name}, None)
            self.__init__()
            self.session_id = str(uuid.uuid4()) # but assign new session_id for clarity in logs/history
        else:
            return 'System Overload', 503 # itm_ta2_eval_controller should prevent this

        self.kdma_training = kdma_training
        self.adm_name = adm_name
        self.adm_profile = adm_profile if adm_profile else 'Unspecified'
        self.itm_scenarios = []
        self.session_type = session_type
        self.history.clear_history()

        ta1_names = []
        if self.session_type == 'eval':
            self.save_history = True
            self.save_history_to_s3 = True
            self.ta1_integration = True
            max_scenarios = None
            ta1_names = ['soartech', 'adept']
        else:
            ta1_names.append(self.session_type)
        if kdma_training:
            self.ta1_integration = True
            self.return_scenario_history = True

        self.history.add_history(
                "Start Session",
                {"session_id": self.session_id,
                "adm_name": self.adm_name,
                "adm_profile": self.adm_profile,
                "session_type": session_type},
                self.session_id)

        if self.ta1_integration and not ITMSession.ta1_connected:
            # Try to get TA1 data, otherwise Fail
            try:
                logging.info("Attempting just-in-time connection to TA1.")
                ITMSession.init_ta1_data(ta1_names)
                ITMSession.ta1_connected = True
            except:
                logging.exception("Exception communicating with TA1; is the TA1 server running?  Ending session.")
                self._end_session() # Exception here ends the session
                return 'Exception communicating with TA1; is the TA1 server running?  Ending session.', 503

        path = f"swagger_server/itm/data/{ITMSession.EVALUATION_TYPE}/scenarios/"
        num_read_scenarios = 0
        for ta1_name in ta1_names:
            scenarios = ITMSession._get_file_names(path, [ITMSession.EVALUATION_TYPE, ta1_name,
                                                          'train' if kdma_training else 'eval'])
            alignment_targets = [target for target in ITMSession.alignment_data[ta1_name]]
            ta1_scenarios = []
            for scenario in scenarios:
                itm_scenario = \
                    ITMScenario(yaml_path=f'{path}{scenario}',
                                session=self, training=self.kdma_training)
                itm_scenario.generate_scenario_data()
                ta1_scenarios.append(itm_scenario)
                for counter in range(1, len(alignment_targets)):
                    ta1_scenarios.append(deepcopy(itm_scenario))

            # if an integrated session, add ta1_controllers to each scenario
            # else, add alignment_targets to each scenario
            if self.ta1_integration:
                controllers = ITMSession.ta1_controllers[ta1_name]
                for scenario_ctr in range(len(ta1_scenarios)):
                    ta1_scenarios[scenario_ctr].set_controller(deepcopy(controllers[scenario_ctr % (len(controllers))]))
            else:
                for scenario_ctr in range(len(ta1_scenarios)):
                    ta1_scenarios[scenario_ctr].alignment_target = alignment_targets[scenario_ctr % (len(alignment_targets))]
            self.itm_scenarios.extend(ta1_scenarios)
            num_read_scenarios += len(ta1_scenarios)
            logging.info('Loaded %d scenarios for %s.', len(ta1_scenarios), ta1_name)

        if max_scenarios is not None and max_scenarios >= num_read_scenarios:
            self.using_max_scenarios = True
            # Fill in extra scenarios with random copies of original scenarios
            while len(self.itm_scenarios) < max_scenarios:
                random_index = random.randint(0, num_read_scenarios - 1)
                self.itm_scenarios.append(deepcopy(self.itm_scenarios[random_index]))

        logging.info('Loaded %d total scenarios.', len(self.itm_scenarios))
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

        message = f"ADM chose action {body.action_type}"
        if body.character_id:
            message += f" with character {body.character_id}"
            if body.parameters:
                message += f" and parameters {body.parameters}"
        elif body.parameters:
            message += f" with parameters {body.parameters}"
        logging.info(message + '.')

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
                logging.exception("Exception getting session alignment; is a TA1 server running?")
                return 'Could not get session alignment; is a TA1 server running?', 503
        else:
            session_alignment = AlignmentResults(alignment_source=[], alignment_target_id=target_id, score=0.5, kdma_values=[])
        logging.info("Got session alignment score %f from TA1 for alignment target id %s.", session_alignment.score, target_id)
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
