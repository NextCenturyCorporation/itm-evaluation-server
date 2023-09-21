import connexion
import time

from swagger_server.models.action import Action  # noqa: E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: E501
from swagger_server.models.scenario import Scenario  # noqa: E501
from swagger_server.models.state import State  # noqa: E501

from ..itm import ITMScenarioSession

MAX_SESSIONS = 3     # Hard limit on simultaneous sessions
#SESSION_TIMEOUT = 60 * 60 * 24  # 24 hour timeout in seconds
SESSION_TIMEOUT = 25  # 10 second timeout in seconds
itm_sessions = {}     # one for each active adm_name
session_mapping = {}  # maps session_id to adm_name and last active time
"""
The internal controller for ITM Server.
"""


def get_alignment_target(session_id, scenario_id):  # noqa: E501
    """Retrieve alignment target for the scenario

    Retrieve alignment target for the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve alignment target
    :type scenario_id: str

    :rtype: AlignmentTarget
    """
    session_dict = session_mapping.get(session_id)
    adm_name = session_dict.get("adm_name") if session_dict else None
    if not adm_name:
        return 'Invalid Session ID', 400
    else: # update access time
        session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}
    return itm_sessions[adm_name].get_alignment_target(scenario_id=scenario_id)


def get_available_actions(session_id, scenario_id):  # noqa: E501
    """Get a list of currently available ADM actions

    Retrieve a list of currently available actions in the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve avaialble actions
    :type scenario_id: str

    :rtype: List[Action]
    """
    session_dict = session_mapping.get(session_id)
    adm_name = session_dict.get("adm_name") if session_dict else None
    if not adm_name:
        return 'Invalid Session ID', 400
    else: # update access time
        session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}
    return itm_sessions[adm_name].get_available_actions(scenario_id=scenario_id)


def get_scenario_state(session_id, scenario_id):  # noqa: E501
    """Retrieve scenario state

    Retrieve state of the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve status
    :type scenario_id: str

    :rtype: State
    """
    session_dict = session_mapping.get(session_id)
    adm_name = session_dict.get("adm_name") if session_dict else None
    if not adm_name:
        return 'Invalid Session ID', 400
    else: # update access time
        session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}
    return itm_sessions[adm_name].get_scenario_state(scenario_id=scenario_id)


def start_scenario(session_id, scenario_id=None):  # noqa: E501
    """Get the next scenario

    Get the next scenario in a session with the specified ADM name, returning a Scenario object and unique id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: a scenario id to start, used internally by TA3
    :type scenario_id: str

    :rtype: Scenario
    """
    session_dict = session_mapping.get(session_id)
    adm_name = session_dict.get("adm_name") if session_dict else None
    if not adm_name:
        return 'Invalid Session ID', 400
    else: # update access time
        session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}
    return itm_sessions[adm_name].start_scenario(scenario_id=scenario_id)

def _reclaim_old_session():
    for session_id in session_mapping.keys():
        session_dict = session_mapping[session_id]
        if time.time() - session_dict["last_accessed"] > SESSION_TIMEOUT:
            print(f'--> Reclaiming OLD session with id {session_id} and adm {session_dict["adm_name"]}')
            session_mapping.pop(session_id)             # Clear out old unused session
            itm_sessions.pop(session_dict["adm_name"])  # From both places
            return ITMScenarioSession()
        else:
            print(f'--> Sorry, session_id {session_id} with adm {session_dict["adm_name"]} is only {time.time() - session_dict["last_accessed"]} milliseconds old.')
    pass

def start_session(adm_name, session_type, kdma_training=None, max_scenarios=None):  # noqa: E501
    """Start a new session

    Get unique session id for grouping answers from a collection of scenarios/probes together # noqa: E501

    :param adm_name: A self-assigned ADM name.  Can add authentication later.
    :type adm_name: str
    :param session_type: the type of session to start (&#x60;test&#x60;, &#x60;eval&#x60;, or a TA1 name)
    :type session_type: str
    :param kdma_training: whether or not this is a training session with TA2
    :type kdma_training: bool
    :param max_scenarios: the maximum number of scenarios requested, supported only in &#x60;test&#x60; sessions
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
            session = ITMScenarioSession()
        itm_sessions[adm_name] = session

    session_id = session.start_session(
        adm_name=adm_name,
        session_type=session_type,
        kdma_training=kdma_training,
        max_scenarios=max_scenarios
    )
    session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}
    print(f"--> Saving session mapping from {session_id} to {session_mapping[session_id]}")
    return session_id


def take_action(session_id, body=None):  # noqa: E501
    """Take an action within a scenario

    Take an action with # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param body: Encapsulation of an action taken by a DM in the context of the scenario
    :type body: dict | bytes

    :rtype: State
    """
    session_dict = session_mapping.get(session_id)
    adm_name = session_dict.get("adm_name") if session_dict else None
    if not adm_name:
        return 'Invalid Session ID', 400
    else: # update access time
        session_mapping[session_id] = {"adm_name": adm_name, "last_accessed": time.time()}

    if connexion.request.is_json:
        body = Action.from_dict(connexion.request.get_json())  # noqa: E501
    return itm_sessions[adm_name].take_action(body=body)
