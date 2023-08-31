import connexion
import six

from swagger_server.models.action import Action  # noqa: E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: E501
from swagger_server.models.scenario import Scenario  # noqa: E501
from swagger_server.models.state import State  # noqa: E501
from swagger_server import util

from ..itm import ITMScenarioSession

ITM_SESSION = ITMScenarioSession()
"""
The internal controller for ITM Server.
`TODO ITM-73: support multiple sessions`
Bonus: add timeouts to inactive clients/sessions
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
    return ITM_SESSION.get_alignment_target(session_id=session_id, scenario_id=scenario_id)


def get_available_actions(session_id, scenario_id):  # noqa: E501
    """Get a list of currently available ADM actions

    Retrieve a list of currently available actions in the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve avaialble actions
    :type scenario_id: str

    :rtype: List[Action]
    """
    return ITM_SESSION.get_available_actions(session_id=session_id, scenario_id=scenario_id)


def get_scenario_state(session_id, scenario_id):  # noqa: E501
    """Retrieve scenario state

    Retrieve state of the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve status
    :type scenario_id: str

    :rtype: State
    """
    return ITM_SESSION.get_scenario_state(session_id=session_id, scenario_id=scenario_id)


def start_scenario(session_id, scenario_id=None):  # noqa: E501
    """Get the next scenario

    Get the next scenario in a session with the specified ADM name, returning a Scenario object and unique id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: a scenario id to start, used internally by TA3
    :type scenario_id: str

    :rtype: Scenario
    """
    return ITM_SESSION.start_scenario(session_id=session_id, scenario_id=scenario_id)


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
    return ITM_SESSION.start_session(
        adm_name=adm_name,
        session_type=session_type,
        kdma_training=kdma_training,
        max_scenarios=max_scenarios
    )


def take_action(session_id, body=None):  # noqa: E501
    """Take an action within a scenario

    Take an action with # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param body: Encapsulation of an action taken by a DM in the context of the scenario
    :type body: dict | bytes

    :rtype: State
    """
    if connexion.request.is_json:
        body = Action.from_dict(connexion.request.get_json())  # noqa: E501
    return ITM_SESSION.take_action(session_id=session_id, body=body)
