import connexion
import time
import builtins
import logging

from swagger_server.models.action import Action  # noqa: E501
from ..itm import ITMSession

MAX_SESSIONS = builtins.max_sessions             # Hard limit on simultaneously active sessions
SESSION_TIMEOUT = 60 * builtins.session_timeout  # Convert timeout to seconds
session_mapping = {}                             # maps session_id to ITMSession and last active time
print(f"Server running with maximum of {MAX_SESSIONS} simultaneous sessions and a session timeout of {SESSION_TIMEOUT} seconds.")
ITMSession.initialize()

"""
The internal controller for ITM Server.
"""

def _get_session(session_id: str) -> ITMSession:
    mapping = session_mapping.get(session_id)
    if mapping:
        # Update access time of existing session and return it
        mapping['last_accessed'] = time.time()
        return mapping['session']
    else:
        return None


def get_alignment_target(session_id, scenario_id):  # noqa: E501
    """Retrieve alignment target for the scenario

    Retrieve alignment target for the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve alignment target
    :type scenario_id: str

    :rtype: Union[AlignmentTarget, Tuple[AlignmentTarget, int], Tuple[AlignmentTarget, int, Dict[str, str]]
    """
    session = _get_session(session_id)
    return session.get_alignment_target(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)

def get_session_alignment(session_id, target_id):  # noqa: E501
    """Retrieve session alignment from TA1

    Retrieve the current session alignment for the session with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param target_id: alignment target id
    :type target_id: str

    :rtype: Union[AlignmentResults, Tuple[AlignmentResults, int], Tuple[AlignmentResults, int, Dict[str, str]]
    """
    session = _get_session(session_id)
    return session.get_session_alignment(target_id=target_id) if session else ('Invalid Session ID', 400)


def get_available_actions(session_id, scenario_id):  # noqa: E501
    """Get a list of currently available ADM actions

    Retrieve a list of currently available actions in the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve available actions
    :type scenario_id: str

    :rtype: Union[List[Action], Tuple[List[Action], int], Tuple[List[Action], int, Dict[str, str]]
    """
    session = _get_session(session_id)
    return session.get_available_actions(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)


def get_scenario_state(session_id, scenario_id):  # noqa: E501
    """Retrieve scenario state

    Retrieve state of the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: the ID of the scenario for which to retrieve status
    :type scenario_id: str

    :rtype: Union[State, Tuple[State, int], Tuple[State, int, Dict[str, str]]
    """
    session = _get_session(session_id)
    return session.get_scenario_state(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)


def start_scenario(session_id, scenario_id=None):  # noqa: E501
    """Get the next scenario

    Get the next scenario in a session with the specified ADM name, returning a Scenario object and unique id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: the scenario id to run; incompatible with /ta2/startSession&#39;s max_scenarios parameter
    :type scenario_id: str

    :rtype: Union[Scenario, Tuple[Scenario, int], Tuple[Scenario, int, Dict[str, str]]
    """
    session = _get_session(session_id)
    return session.start_scenario(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)


def _reclaim_old_session():
    # First look for a completed session
    old_session_id = None
    for mapping in session_mapping.values():
        session: ITMSession = mapping['session']
        if session.session_complete:            # This session terminated normally
            old_session_id = session.session_id # Save the old id
            logging.info(f"Reclaiming completed session {old_session_id}, name '{session.adm_name}'")
            session.__init__()                  # And re-initialize the session
            break

    if old_session_id:
        session_mapping.pop(old_session_id)     # Remove the entry in the session_mapping for the old session_id
        return session                          # And return the re-initialized session

    # Next look for an inactive session
    current_time = time.time()
    for mapping in session_mapping.values():
        if current_time - mapping['last_accessed'] > SESSION_TIMEOUT: # This session is inactive
            session: ITMSession = mapping['session']
            old_session_id = session.session_id # Save the old id
            logging.info(f"Reclaiming inactive session {old_session_id}, name '{session.adm_name}'")
            session.__init__()                  # And re-initialize the session
            break

    if old_session_id:
        session_mapping.pop(old_session_id)     # Remove the entry in the session_mapping for the old session_id
        return session                          # And return the re-initialized session

    logging.info("Couldn't reclaim a session")
    return None # No session to reclaim


def start_session(adm_name, session_type, adm_profile=None, domain=None, kdma_training=None, max_scenarios=None):  # noqa: E501
    """Start a new session

    Get unique session id for grouping answers from a collection of scenarios together # noqa: E501

    :param adm_name: A self-assigned ADM name.
    :type adm_name: str
    :param session_type: the type of session to start (&#x60;eval&#x60;, &#x60;test&#x60;, or a TA1 name)
    :type session_type: str
    :param adm_profile: a profile of the ADM in terms of its alignment strategy
    :type adm_profile: str
    :param domain: A domain supported by the ITM evaluation server
    :type domain: str
    :param kdma_training: whether this is a &#x60;full&#x60;, &#x60;solo&#x60;, or non-training session with TA2
    :type kdma_training: str
    :param max_scenarios: the maximum number of scenarios requested, not supported in &#x60;eval&#x60; sessions
    :type max_scenarios: int

    :rtype: Union[str, Tuple[str, int], Tuple[str, int, Dict[str, str]]
    """

    if len(session_mapping) >= MAX_SESSIONS:
        session = _reclaim_old_session()
        if not session: # couldn't clear out an old session
            return 'System Overload', 503
    else:
        session = ITMSession()

    session_id = session.start_session(
        adm_name=adm_name,
        session_type=session_type,
        adm_profile=adm_profile if adm_profile != 'None' else None,
        domain=domain if domain != 'None' else None,
        kdma_training=kdma_training if kdma_training != 'None' else None,
        max_scenarios=max_scenarios
    )
    logging.info(f"Saving session_id {session_id} in mapping; name '{session.adm_name}'.")
    session_mapping[session_id] = {'session': session, 'last_accessed': time.time()}
    return session_id


def take_action(session_id, body=None):  # noqa: E501
    """Take an action within a scenario

    Take the specified Action within a scenario # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param action: Encapsulation of an action taken by a DM in the context of the scenario
    :type action: dict | bytes

    :rtype: Union[State, Tuple[State, int], Tuple[State, int, Dict[str, str]]
    """
    if connexion.request.is_json:
        body = Action.from_dict(connexion.request.get_json())  # noqa: E501

    session = _get_session(session_id)
    return session.take_action(body=body) if session else ('Invalid Session ID', 400)


def intend_action(session_id, body=None):  # noqa: E501
    """Express intent to take an action within a scenario

    Express intent to take the specified Action within a scenario # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param body: Encapsulation of the intended action by a DM in the context of the scenario
    :type body: dict | bytes

    :rtype: Union[State, Tuple[State, int], Tuple[State, int, Dict[str, str]]
    """
    if connexion.request.is_json:
        body = Action.from_dict(connexion.request.get_json())  # noqa: E501

    session = _get_session(session_id)
    return session.intend_action(body=body) if session else ('Invalid Session ID', 400)


def validate_action(session_id, body=None):  # noqa: E501
    """Validate that the specified Action is structually and contextually valid within a scenario

    Validate that the specified Action is structually and contextually valid within a scenario # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param body: Encapsulation of an action to be validated by a DM in the context of the scenario
    :type body: dict | bytes

    :rtype: Union[boolean, Tuple[str, int], Tuple[str, int, Dict[str, str]]
    """
    if connexion.request.is_json:
        body = Action.from_dict(connexion.request.get_json())  # noqa: E501

    session = _get_session(session_id)
    return session.validate_action(body=body) if session else ('Invalid Session ID', 400)
