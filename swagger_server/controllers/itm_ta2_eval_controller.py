import connexion
import time

from swagger_server.models.action import Action  # noqa: E501
from ..itm import ITMSession

MAX_SESSIONS = 250     # Hard limit on simultaneously active sessions
SESSION_TIMEOUT = 60 * 60 * 1  # 1 hour timeout in seconds
itm_sessions = {}     # one for each active adm_name
session_mapping = {}  # maps session_id to adm_name and last active time
ITMSession.initialize()

"""
The internal controller for ITM Server.
"""

def _get_session(session_id: str) -> ITMSession:
    session_dict = session_mapping.get(session_id)
    adm_name = session_dict.get("adm_name") if session_dict else None
    if not adm_name:
        return None

    # Update access time and return session
    session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}
    return itm_sessions[adm_name]

def get_alignment_target(session_id, scenario_id):  # noqa: E501
    """Retrieve alignment target for the scenario

    Retrieve alignment target for the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve alignment target
    :type scenario_id: str

    :rtype: AlignmentTarget
    """
    session = _get_session(session_id)
    return session.get_alignment_target(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)

def get_session_alignment(session_id, target_id):  # noqa: E501
    """Retrieve current session alignment

    Retrieve current session alignment for the session with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str

    :rtype: AlignmentResults
    """
    session = _get_session(session_id)
    return session.get_session_alignment(target_id=target_id) if session else ('Invalid Session ID', 400)


def get_available_actions(session_id, scenario_id):  # noqa: E501
    """Get a list of currently available ADM actions

    Retrieve a list of currently available actions in the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve avaialble actions
    :type scenario_id: str

    :rtype: List[Action]
    """
    session = _get_session(session_id)
    return session.get_available_actions(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)


def get_scenario_state(session_id, scenario_id):  # noqa: E501
    """Retrieve scenario state

    Retrieve state of the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve status
    :type scenario_id: str

    :rtype: State
    """
    session = _get_session(session_id)
    return session.get_scenario_state(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)


def start_scenario(session_id, scenario_id=None):  # noqa: E501
    """Get the next scenario

    Get the next scenario in a session with the specified ADM name, returning a Scenario object and unique id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: the scenario id to run; incompatible with /ta2/startSession's max_scenarios parameter
    :type scenario_id: str

    :rtype: Scenario
    """
    session = _get_session(session_id)
    return session.start_scenario(scenario_id=scenario_id) if session else ('Invalid Session ID', 400)

def _reclaim_old_session():
    for session_id in session_mapping.keys():
        session_dict = session_mapping[session_id]
        if time.time() - session_dict["last_accessed"] > SESSION_TIMEOUT:
            itm_sessions.pop(session_dict["adm_name"])  # Clear out old unused session
            session_mapping.pop(session_id)             # From both places
            return ITMSession()
    return None

def start_session(adm_name, session_type, adm_profile=None, kdma_training=None, max_scenarios=None):  # noqa: E501
    """Start a new session

    Get unique session id for grouping answers from a collection of scenarios/probes together # noqa: E501

    :param adm_name: A self-assigned ADM name.
    :type adm_name: str
    :param session_type: the type of session to start (`eval`, `test`, or a TA1 name)
    :type session_type: str
    :param adm_profile: a profile of the ADM in terms of its alignment strategy
    :type adm_profile: str
    :param kdma_training: whether this is a `full`, `solo`, or non-training session with TA2
    :type kdma_training: str
    :param max_scenarios: the maximum number of scenarios requested, supported only in `test` sessions
    :type max_scenarios: int

    :rtype: str
    """

    session = itm_sessions.get(adm_name)
    if not session:
        if len(itm_sessions) >= MAX_SESSIONS:
            session = _reclaim_old_session()
            if not session: # couldn't clear out an old session
                return 'System Overload', 503
        else:
            session = ITMSession()
        itm_sessions[adm_name] = session
    else:
        # Iterate through session_mappings, looking for the one whose dict contains the specified adm_name.
        # Then remove that session mapping.
        old_session_id = None
        for session_id in session_mapping.keys():
            session_dict = session_mapping[session_id]
            if session_dict["adm_name"] == adm_name:
                old_session_id = session_id
        if old_session_id:
            session_mapping.pop(old_session_id) # Remove old session_id from mapping since session is about to get new id

    session_id = session.start_session(
        adm_name=adm_name,
        session_type=session_type,
        adm_profile=adm_profile if adm_profile != 'None' else None,
        kdma_training=kdma_training if kdma_training != 'None' else None,
        adept_populations=True,
        max_scenarios=max_scenarios
    )
    session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}
    return session_id


def take_action(session_id, body=None):  # noqa: E501
    """Take an action within a scenario

    Take the specified Action within a scenario # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param body: Encapsulation of an action taken by a DM in the context of the scenario
    :type body: dict | bytes

    :rtype: State
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

    :rtype: State
    """
    if connexion.request.is_json:
        body = Action.from_dict(connexion.request.get_json())  # noqa: E501

    session = _get_session(session_id)
    return session.intend_action(body=body) if session else ('Invalid Session ID', 400)
