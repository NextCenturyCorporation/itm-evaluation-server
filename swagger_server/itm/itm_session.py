import time
import uuid
import random
import os
import logging
import builtins
from datetime import datetime
from typing import List
from copy import deepcopy
from json import dumps
from requests import exceptions
from swagger_server.models import (
    Action,
    AlignmentTarget,
    AlignmentResults,
    KDMAValue,
    Scenario,
    State,
    MetaInfo
)
from .itm_scenario import ITMScenario
from .itm_action_handler import ITMActionHandler
from swagger_server.itm.ta1.itm_ta1_controller import ITMTa1Controller
from .itm_history import ITMHistory
from .itm_domain_config import ITMDomainConfig, ITMDomainConfigFactory
from swagger_server import config_util

class ITMSession:
    """
    Class for representing and manipulating a simulation scenario session.
    """
    config_util.check_ini()
    config = config_util.read_ini()[0]
    config_group = builtins.config_group

    # Class variables
    EVALUATION_TYPE = config[config_group]['EVALUATION_TYPE']
    EVALUATION_NAME = config[config_group]['EVAL_NAME']
    EVALUATION_NUMBER = config[config_group]['EVAL_NUMBER']
    DEFAULT_DOMAIN = config[config_group]['DEFAULT_DOMAIN']
    SUPPORTED_DOMAINS = config[config_group]['SUPPORTED_DOMAINS']
    SCENARIO_DIRECTORY = config[config_group]['SCENARIO_DIRECTORY']
    ALL_TA1_NAMES = config[config_group]['ALL_TA1_NAMES'].replace('\n','').split(',')

    # maps alignment id to list alignment_targets, as limited by configuration; used whether connecting to TA1 or not
    alignment_data = {}
    # have we successfully connected to TA1?
    ta1_connected = False
    # maps ta1_name to list of alignment target IDs obtained from the TA1 server
    alignment_ids = {}
    # This determines whether the server makes calls to TA1
    ta1_integration = not builtins.testing
    # This determines whether the server saves history to JSON
    save_history = config[config_group].getboolean("SAVE_HISTORY")
    # save_history must also be True
    save_history_to_s3 = config[config_group].getboolean("SAVE_HISTORY_TO_S3")


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
        self.domain = ''
        self.using_max_scenarios = False
        self.kdma_training = None

        self.session_complete = False
        self.state: State = None
        self.current_scenario_index = 0
        self.itm_scenarios = []
        self.itm_scenario: ITMScenario = None

        # Domain config
        self.domain_config: ITMDomainConfig = None
        # Action Handler
        self.action_handler: ITMActionHandler = None
        # ADM History
        self.history: ITMHistory = ITMHistory(ITMSession.config)
        # This determines whether the server returns history in final State after each scenario completes
        self.return_scenario_history = False

    def __deepcopy__(self, memo):
        return self # Allows us to deepcopy ITMScenarios

    @staticmethod
    def initialize():
        logging.basicConfig(level=logging.INFO, format='%(levelname)s %(asctime)s %(message)s', datefmt='%m-%d %I:%M:%S')
        if ITMSession.ta1_integration:
            try:
                logging.info("Loading TA1 configuration from TA1 servers...")
                ITMSession.init_ta1_data(ITMSession.ALL_TA1_NAMES)
                ITMSession.ta1_connected = True
                logging.info("Done.")
            except Exception as e:
                logging.warning("Could not initialize TA1 data. Running standalone.")
                logging.exception(e)
        else:
            logging.info("Running server in testing mode; no connection to TA1 servers.")


    @staticmethod
    def init_ta1_data(ta1_names):
        # Populate alignment_data_ids from ITMTa1Controller.get_alignment_target_ids
        for ta1_name in ta1_names:
            ITMSession.alignment_ids[ta1_name] = [
                alignment_target_id for alignment_target_id in ITMTa1Controller.get_alignment_target_ids(ta1_name)
            ]


    def load_alignment_target(self, target_id, ta1_name):
        alignment_target = ITMSession.alignment_data.get(target_id)
        if alignment_target: # Previously retrieved specified alignment target
            return alignment_target
        if self.ta1_integration:
            if target_id not in ITMSession.alignment_ids[ta1_name]:
                logging.fatal(f"Cannot get alignment target {target_id} because it is not defined by {ta1_name}. Check configuration.")
                raise Exception("Undefined alignment target")
            else:
                logging.info(f"Loading alignment target {target_id} from TA1 {ta1_name}.")
                alignment_target = ITMTa1Controller.get_alignment_target(ta1_name, target_id)
        else:
            alignment_target = AlignmentTarget(target_id, [KDMAValue(kdma='Test_KDMA', value=0.5)])
        ITMSession.alignment_data[target_id] = alignment_target
        return alignment_target


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
                session_alignment: AlignmentResults = \
                    self.itm_scenario.ta1_controller.get_session_alignment()
                session_alignment_score = session_alignment.score
                self.history.add_history(
                    "TA1 Session Alignment",
                    {"session_id": self.itm_scenario.ta1_controller.session_id,
                    "target_id": self.itm_scenario.ta1_controller.alignment_target_id},
                    session_alignment.to_dict()
                )
                logging.info("Got session alignment score %s from TA1.", session_alignment_score)
                if session_alignment.alignment_source:
                    alignment_scenario_id = session_alignment.alignment_source[0].scenario_id
                    if self.itm_scenario.id != alignment_scenario_id:
                        logging.warning("\033[92mContamination in session_alignment! scenario is %s but alignment source scenario is %s.\033[00m",
                                        self.itm_scenario.id, alignment_scenario_id)
            except exceptions.HTTPError:
                logging.exception("HTTPError from TA1 getting session alignment.")
            except Exception:
                logging.exception("Exception getting session alignment. Ignoring.")

        if (self.session_type != 'test'):
            self.state.unstructured = f'Scenario {self.itm_scenario.id} complete for target {self.itm_scenario.alignment_target.id}. Session alignment score = {session_alignment_score}'
        else:
            self.state.unstructured = f'Test scenario {self.itm_scenario.id} complete.'
        self._cleanup()


    def _cleanup(self):
        if self.save_history:
            kdma = self.itm_scenario.alignment_target.kdma_values[0].kdma.split(" ")[0].lower()
            value = self.itm_scenario.alignment_target.kdma_values[0].value
            if not value:
                value = self.itm_scenario.alignment_target.id
            alignment_type = kdma + "-" + str(value)
            timestamp = f"{datetime.now():%Y%m%d-%H.%M.%S}" # e.g., 20240821-18.22.53
            filename = f"{self.adm_profile.replace(' ','-')}-" if self.adm_profile else ''
            filename += f"{ITMSession.EVALUATION_TYPE.replace(' ','')}-{self.itm_scenario.id.replace(' ', '_')}-{self.itm_scenario.scene_type}-{alignment_type.replace(' ', '_')}-{self.adm_name}-{timestamp}"
            self.history.write_to_json_file(filename, self.save_history_to_s3)
        if self.return_scenario_history:
            if builtins.testing:
                self.state.unstructured = "Full session history"
            else:
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

        self.history.add_history(
            "Get Alignment Target",
            {"scenario_id": self.itm_scenario.id, "session_id": self.session_id},
            self.itm_scenario.alignment_target.to_dict() if self.itm_scenario.alignment_target else None)

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
                return f'Scenario ID `{scenario_id}` does not exist as {"a training" if self.kdma_training else "an eval"} scenario for `{self.session_type}`. Check your TA3 server configuration?', 404
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
            self.itm_scenario.clear_hidden_data(self.state)
            self.state.meta_info = MetaInfo(scene_id=self.itm_scenario.isd.current_scene.id, probe_response=None)
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
                {"session_id": self.session_id, "adm_name": self.adm_name, "adm_profile": self.adm_profile},
                scenario.to_dict())
            logging.info("Scenario %s starting.", self.itm_scenario.id)

            if self.ta1_integration:
                try:
                    user_id = f"{self.session_id}_{self.itm_scenario.id}"
                    ta1_session_id = self.itm_scenario.ta1_controller.new_session(context=user_id)
                    self.history.add_history(
                        "TA1 Session ID", {}, ta1_session_id
                    )
                    logging.info("Got new session_id '%s' from TA1.", ta1_session_id)
                except exceptions.HTTPError:
                    self._end_session() # Exception here ends the session
                    logging.exception("HTTPError from TA1 starting session.")
                    return 'Could not get new session.  Ending session.', 503
                except:
                    logging.exception("Exception communicating with TA1; is the TA1 server running?  Ending session.")
                    self._end_session() # Exception here ends the session
                    return 'Exception communicating with TA1; is the TA1 server running?  Ending session.', 503

            # Get alignment target; was previously obtained from TA1 unless testing.
            if not self.kdma_training:
                alignment_target = self.itm_scenario.alignment_target
                logging.info("Using alignment target %s.", alignment_target.id)
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

    def start_session(self, adm_name: str, session_type: str, adm_profile: str, domain: str, kdma_training: str=None, max_scenarios=None) -> str:
        """
        Start a new session.

        Args:
            adm_name: The ADM name associated with the session.
            session_type: The type of session: either one of the configured TA1 names, `test`, or `eval`
            adm_profile: a profile of the ADM in terms of its alignment strategy
            domain: the session domain, as selected from the configured `SUPPORTED_DOMAINS`;
                defaults to the configured `DEFAULT_DOMAIN`
            kdma_training: whether this is a `full`, `solo`, or non-training session with TA2;
                default to non-training
            max_scenarios: The max number of scenarios presented during the session

        Returns:
            A new session Id to use in subsequent calls
        """
        if session_type not in ITMSession.ALL_TA1_NAMES and session_type not in ['eval', 'test']:
            ta1_name_str = ''
            for ta1_name in ITMSession.ALL_TA1_NAMES:
                ta1_name_str += ta1_name + ", "
            return (
                f'Invalid session type `{session_type}`. Must be {ta1_name_str}test, or eval',
                400
            )

        # Re-use current session for same ADM after a client crash
        if self.session_id is None:
            self.session_id = str(uuid.uuid4())
        elif self.adm_name == adm_name:
            logging.info("Re-using session %s for ADM %s", self.session_id, self.adm_name)
            self.history.add_history(
                "Abort Session", {"session_id": self.session_id, "adm_name": self.adm_name, "domain": self.domain}, None)
            self.__init__()
            self.session_id = str(uuid.uuid4()) # but assign new session_id for clarity in logs/history
        else:
            return 'System Overload', 503 # itm_ta2_eval_controller should prevent this

        # Set up domain
        if domain is None:
            domain = ITMSession.DEFAULT_DOMAIN
        elif domain not in self.SUPPORTED_DOMAINS:
            return f"Unsupported domain `{domain}`", 400
        self.domain = domain
        self.domain_config = ITMDomainConfigFactory.create_domain_factory(domain)
        if not self.domain_config:
            return f"No config class found for domain `{domain}`", 400
        self.action_handler = self.domain_config.get_action_handler(self)
        if not self.action_handler:
            return f"No action handler found for domain `{domain}`", 400

        self.kdma_training = kdma_training
        self.adm_name = adm_name
        self.adm_profile = adm_profile if adm_profile else ''
        if max_scenarios == 0:
            max_scenarios = None
        self.itm_scenarios = []
        self.session_type = session_type
        self.history.clear_history()

        ta1_names = []
        if self.session_type == 'eval':
            self.ta1_integration = True
            max_scenarios = None
            ta1_names = ITMSession.ALL_TA1_NAMES
        else:
            ta1_names.append(self.session_type)
        if kdma_training:
            self.return_scenario_history = True
            self.ta1_integration = kdma_training == 'full'
        if session_type == 'test':
            self.ta1_integration = False

        self.history.add_history(
                "Start Session",
                {"session_id": self.session_id,
                "adm_name": self.adm_name,
                "adm_profile": self.adm_profile,
                "domain": self.domain,
                "session_type": session_type},
                self.session_id)

        if self.ta1_integration and not ITMSession.ta1_connected:
            # Try to get TA1 data, otherwise Fail
            try:
                logging.info("Attempting just-in-time connection to TA1.")
                ITMSession.init_ta1_data(ta1_names)
                ITMSession.ta1_connected = True
                logging.info("Just-in-time connection succeeded.")
            except:
                logging.exception("Exception communicating with TA1; is the TA1 server running?  Ending session.")
                self._end_session() # Exception here ends the session
                return 'Exception communicating with TA1; is the TA1 server running?  Ending session.', 503

        # Get scenario path based on evaluation type and number
        if self.session_type != 'test':
            scenario_path = f"{ITMSession.SCENARIO_DIRECTORY}/"
        elif ITMSession.EVALUATION_NUMBER <= '5': # through Phase 1
            scenario_path = f"swagger_server/itm/data/{ITMSession.EVALUATION_TYPE}/test/"
        else: # after Phase 1
            scenario_path = f"swagger_server/itm/data/domains/{domain}/test/"

        num_read_scenarios = 0
        for ta1_name in ta1_names:
            if self.session_type == 'test':
                scenarios = ITMSession._get_file_names(scenario_path)
            else:
                scenarios = ITMTa1Controller.get_filenames(ta1_name, kdma_training)

            ta1_scenarios = []
            scenario_ctr = 0
            for scenario in scenarios:
                itm_scenario = \
                    self.domain_config.get_scenario(yaml_path=f'{scenario_path}{scenario}',
                                session=self, training=self.kdma_training)
                try:
                    itm_scenario.generate_scenario_data()
                except FileNotFoundError as fnfe:
                    logging.fatal("Could not read filename '%s.'  Check your TA3 server configuration?", fnfe.filename)
                    return f"Could not read filename '{fnfe.filename}.'  Check your TA3 server configuration?", 503

                if ta1_name == "test":
                    ta1_scenarios.append(deepcopy(itm_scenario))
                    ta1_scenarios[scenario_ctr].alignment_target = AlignmentTarget('Test_Target_ID', [KDMAValue(kdma='Test_KDMA', value=0.5)])
                    scenario_ctr += 1
                else:
                    def __load_scenarios(alignment_target_ids, scenario_ctr):
                        for target_id in alignment_target_ids:
                            try:
                                ta1_scenarios.append(deepcopy(itm_scenario))
                                alignment_target = self.load_alignment_target(target_id, ta1_name)
                                ta1_scenarios[scenario_ctr].alignment_target = alignment_target
                                if self.ta1_integration:
                                    ta1_scenarios[scenario_ctr].set_controller( # Always create a new controller for each scenario.
                                        ITMTa1Controller.create_controller(ta1_name, target_id, alignment_target))
                                scenario_ctr += 1
                            except Exception as e:
                                logging.fatal(f"Couldn't obtain alignment target '{target_id}'. Check your TA3 server configuration or connection to TA1.")
                                raise e
                        return scenario_ctr

                    try:
                        # Get a list of alignment target IDs that apply to the given scenario so we can create a scenario for each target
                        scenario_ctr = __load_scenarios(ITMTa1Controller.get_target_ids(ta1_name, itm_scenario), scenario_ctr)
                    except Exception as e:
                        logging.exception(e)
                        return f"Problem loading TA3 server configuration.", 503

            self.itm_scenarios.extend(ta1_scenarios)
            num_read_scenarios += len(ta1_scenarios)
            logging.info('Loaded %d scenarios for %s.', len(ta1_scenarios), ta1_name)

        scenario_ctr = 0
        logging.info("Scenario load summary:")
        for scenario in self.itm_scenarios:
            logging.info(f'  Scenario #{scenario_ctr} has ID {scenario.id} and alignment target {scenario.alignment_target.id}.')
            scenario_ctr += 1

        if max_scenarios is not None and max_scenarios >= num_read_scenarios:
            self.using_max_scenarios = True
            # Fill in extra scenarios with random copies of original scenarios
            while len(self.itm_scenarios) < max_scenarios:
                random_index = random.randint(0, num_read_scenarios - 1)
                self.itm_scenarios.append(deepcopy(self.itm_scenarios[random_index]))

        logging.info("Loaded %d total scenarios from '%s'.", len(self.itm_scenarios), scenario_path)
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
        return self.take_or_intend_action(body, False)


    def intend_action(self, body: Action) -> State:
        """
        Intend an action within a scenario

        Args:
            body: Encapsulation of an action intended by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """
        return self.take_or_intend_action(body, True)


    def prevalidate_action(self, adm_action: Action) -> str:
        """
        Ensure that an ADM's version of a given action (by action_id) matches the scene's.

        Args:
            adm_action: the Action that the ADM sent

        Returns:
            Either an error string, or None if prevalidation passes
        """
        scene_mapping = None
        for mapping in self.itm_scenario.isd.current_scene.action_mappings:
            if mapping.action_id == adm_action.action_id:
                scene_mapping = mapping
                break

        # If the ADM action is not from an action_mapping, then pre-validation doesn't apply and there's no error.
        if not scene_mapping:
            return None

        # If we found the action in the action mappings, validate the adm action against it
        scene_action = Action(action_id=scene_mapping.action_id,
                              action_type=scene_mapping.action_type,
                              intent_action=scene_mapping.intent_action,
                              character_id=scene_mapping.character_id,
                              parameters=scene_mapping.parameters
                              )

        if adm_action.action_type != scene_action.action_type:
            return f"ADM action_type ({adm_action.action_type}) doesn't match scene ({scene_action.action_type}) for action_id '{adm_action.action_id}'."
        if adm_action.intent_action != scene_action.intent_action:
            return f"ADM intent_action ({adm_action.intent_action}) doesn't match scene ({scene_action.intent_action}) for action_id '{adm_action.action_id}'."
        if scene_action.character_id and adm_action.character_id != scene_action.character_id:
            return f"ADM character_id ({adm_action.character_id}) doesn't match scene ({scene_action.character_id}) for action_id '{adm_action.action_id}'."
        if scene_action.parameters:
            for key in scene_action.parameters.keys():
                if not adm_action.parameters:
                    return f"Action parameter '{key}' missing from ADM action for action_id '{adm_action.action_id}'."
                scene_value = scene_action.parameters.get(key)
                adm_value = adm_action.parameters.get(key)
                if scene_value and adm_value != scene_value:
                    return f"ADM value for parameter '{key}' doesn't match scene for action_id '{adm_action.action_id}': ({adm_value} != {scene_value})."

        # Everything passes
        return None


    def take_or_intend_action(self, adm_action: Action, intent_only) -> State:
        """
        Take or intend an action within a scenario

        Args:
            body: Encapsulation of an action taken or intended by a DM in the context of the scenario

        Returns:
            The current state of the scenario as a State object.
        """

        message = f"ADM {'intended' if intent_only else 'chose'} action {adm_action.action_type}"
        if adm_action.character_id:
            message += f" with character {adm_action.character_id}"
            if adm_action.parameters:
                message += f" and parameters {adm_action.parameters}"
        elif adm_action.parameters:
            message += f" with parameters {adm_action.parameters}"
        logging.info(message + '.')

        # Pre-validate action.  This ensures the ADM didn't change a pre-configured action in ways it shouldn't
        prevalidation_error = self.prevalidate_action(adm_action)
        if prevalidation_error:
            return prevalidation_error, 400

        # Validate the right type of action (taken or intended)
        if intent_only and not adm_action.intent_action:
            return 'Cannot take actions via intent_action', 400
        elif adm_action.intent_action and not intent_only:
            return 'Cannot intend actions via take_action', 400

        # Validate that action is a valid, well-formed action
        (successful, message, code) = self.action_handler.validate_action(adm_action)
        if not successful:
            return message, code

        if intent_only:
            self.action_handler.process_intention(action=adm_action)
        else:
            self.action_handler.process_action(action=adm_action)
        return self.state


    def get_session_alignment(self, target_id: str) -> AlignmentResults:
        if not self.kdma_training == 'full':
            return 'Session alignment can only be requested during a full training session', 403

        session_alignment: AlignmentResults = None
        if self.ta1_integration:
            try:
                if len(self.itm_scenario.probes_sent) > 0:
                    session_alignment = \
                        self.itm_scenario.ta1_controller.get_session_alignment(target_id=target_id)
                    session_alignment.alignment_target_id = target_id
                else:
                    session_alignment = AlignmentResults(alignment_source=[], alignment_target_id=target_id, score=0.5)

            except:
                logging.exception("Exception getting session alignment; is a TA1 server running?")
                return 'Could not get session alignment; is a TA1 server running?', 503
        else:
            session_alignment = AlignmentResults(alignment_source=[], alignment_target_id=target_id, score=0.5)
        logging.info("Got session alignment score %f from TA1 for alignment target id %s.", session_alignment.score, target_id)
        self.history.add_history(
            "Get Session Alignment",
            {"scenario_id": self.itm_scenario.id, "session_id": self.session_id, "target_id": target_id},
            session_alignment.to_dict() if session_alignment else None)

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
