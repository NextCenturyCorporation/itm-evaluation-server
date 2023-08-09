import connexion
import six

from swagger_server.models.action import Action  # noqa: E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: E501
from swagger_server.models.scenario import Scenario  # noqa: E501
from swagger_server.models.state import State  # noqa: E501
from swagger_server.models.vitals import Vitals  # noqa: E501
from swagger_server import util

from ..itm import ITMScenarioSession

ITM_SESSION = ITMScenarioSession()
"""
The internal controller for ITM Server.
`TODO support multiple sessions on the same server simultaneously`
"""


def apply_decompression_needle(session_id, casualty_id, location):  # noqa: E501
    """Apply a decompression needle to a casualty

    Treat the specified casualty with a decompression needle in the specified location # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to treat
    :type casualty_id: str
    :param location: the injury location on the casualty&#x27;s body (see Injury &#x60;location&#x60;)
    :type location: str

    :rtype: State
    """
    return 'do some magic!'


def apply_hemostatic_gauze(session_id, casualty_id, location):  # noqa: E501
    """Apply hemostatic gauze to a casualty

    Treat the specified casualty with hemostatic gauze in the specified location # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to treat
    :type casualty_id: str
    :param location: the injury location on the casualty&#x27;s body (see Injury &#x60;location&#x60;)
    :type location: str

    :rtype: State
    """
    return 'do some magic!'


def apply_nasal_trumpet(session_id, casualty_id):  # noqa: E501
    """Apply a nasal trumpet to a casualty

    Treat the specified casualty with a nasal trumpet in the specified location # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to treat
    :type casualty_id: str

    :rtype: State
    """
    return 'do some magic!'


def apply_pressure_bandage(session_id, casualty_id, location):  # noqa: E501
    """Apply a pressure bandage to a casualty

    Treat the specified casualty with a pressure bandage in the specified location # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to treat
    :type casualty_id: str
    :param location: the injury location on the casualty&#x27;s body (see Injury &#x60;location&#x60;)
    :type location: str

    :rtype: State
    """
    return 'do some magic!'


def apply_tourniquet(session_id, casualty_id, location):  # noqa: E501
    """Apply a tourniquet to a casualty

    Treat the specified casualty with a tourniquet in the specified location # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to treat
    :type casualty_id: str
    :param location: the injury location on the casualty&#x27;s body (see Injury &#x60;location&#x60;)
    :type location: str

    :rtype: State
    """
    return 'do some magic!'


def apply_treatment(session_id, casualty_id, tool, location=None):  # noqa: E501
    """Apply a treatment to a casualty

    Treat the specified casualty with the specified tool in the specified location # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to tag
    :type casualty_id: str
    :param tool: The tool to use to apply treatment (see Supplies)
    :type tool: str
    :param location: the injury location on the casualty&#x27;s body (see Injury &#x60;location&#x60;)
    :type location: str

    :rtype: State
    """
    return 'do some magic!'


def check_vital(session_id, casualty_id, vital_sign):  # noqa: E501
    """Assess and retrieve a vital sign

    Retrieve the specified vital sign of the specified casualty. # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to query
    :type casualty_id: str
    :param vital_sign: The vital sign to retrieve, taken from controlled vocabulary
    :type vital_sign: str

    :rtype: Vitals
    """
    return 'do some magic!'


def check_vitals(session_id, casualty_id):  # noqa: E501
    """Assess and retrieve all casualty vital signs

    Retrieve all vital signs of the specified casualty. # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to query
    :type casualty_id: str

    :rtype: Vitals
    """
    return ITM_SESSION.get_vitals(session_id=session_id, casualty_id=casualty_id)


def direct_to_safezone(session_id, scenario_id):  # noqa: E501
    """Direct casualties to the safe zone

    Verbally direct all mobile casualties to the safe zone # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario to direct mobile casualties
    :type scenario_id: str

    :rtype: State
    """
    return 'do some magic!'


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
    return 'do some magic!'


def get_available_actions2(session_id, scenario_id):  # noqa: E501
    """Get a list of currently available ADM action types

    Retrieve a list of currently available actions in the scenario with the specified id # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param scenario_id: The ID of the scenario for which to retrieve avaialble actions
    :type scenario_id: str

    :rtype: List[str]
    """
    return 'do some magic!'


def get_consciousness(session_id, casualty_id):  # noqa: E501
    """Check casualty consciousness

    Check the consciousness of the specified casualty # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to for which to check consciousness
    :type casualty_id: str

    :rtype: bool
    """
    return 'do some magic!'


def get_heart_rate(session_id, casualty_id):  # noqa: E501
    """Check casualty heart rate

    Check the heart rate of the specified casualty. # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to for which to request heart rate
    :type casualty_id: str

    :rtype: int
    """
    return ITM_SESSION.get_heart_rate(session_id=session_id, casualty_id=casualty_id)


def get_respiratory_rate(session_id, casualty_id):  # noqa: E501
    """Check casualty respiratory rate

    Check the respiratory rate of the specified casualty. # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to for which to request respiratory rate
    :type casualty_id: str

    :rtype: int
    """
    return 'do some magic!'


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


def start_session(adm_name, session_type, max_scenarios=None):  # noqa: E501
    """Start a new session

    Get unique session id for grouping answers from a collection of scenarios/probes together # noqa: E501

    :param adm_name: A self-assigned ADM name.  Can add authentication later.
    :type adm_name: str
    :param session_type: the type of session to start (&#x60;test&#x60;, &#x60;eval&#x60;, or a TA1 name)
    :type session_type: str
    :param max_scenarios: the maximum number of scenarios requested, supported only in &#x60;test&#x60; sessions
    :type max_scenarios: int

    :rtype: str
    """
    return ITM_SESSION.start_session(
        adm_name=adm_name,
        session_type=session_type,
        max_scenarios=max_scenarios,
    )


def tag_casualty(session_id, casualty_id, tag):  # noqa: E501
    """Tag a casualty with a triage category

    Apply a triage tag to the specified casualty with the specified tag # noqa: E501

    :param session_id: a unique session_id, as returned by /ta2/startSession
    :type session_id: str
    :param casualty_id: The ID of the casualty to tag
    :type casualty_id: str
    :param tag: The tag to apply to the casualty, chosen from triage categories
    :type tag: str

    :rtype: State
    """
    return ITM_SESSION.tag_casualty(session_id=session_id, casualty_id=casualty_id, tag=tag)


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
    return 'do some magic!'
