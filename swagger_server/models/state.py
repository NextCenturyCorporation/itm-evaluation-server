# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.character import Character  # noqa: F401,E501
from swagger_server.models.environment import Environment  # noqa: F401,E501
from swagger_server.models.meta_info import MetaInfo  # noqa: F401,E501
from swagger_server.models.mission import Mission  # noqa: F401,E501
from swagger_server.models.supplies import Supplies  # noqa: F401,E501
from swagger_server.models.threat_state import ThreatState  # noqa: F401,E501
from swagger_server import util


class State(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, unstructured: str=None, elapsed_time: int=None, meta_info: MetaInfo=None, scenario_complete: bool=None, mission: Mission=None, environment: Environment=None, threat_state: ThreatState=None, supplies: List[Supplies]=None, characters: List[Character]=None):  # noqa: E501
        """State - a model defined in Swagger

        :param unstructured: The unstructured of this State.  # noqa: E501
        :type unstructured: str
        :param elapsed_time: The elapsed_time of this State.  # noqa: E501
        :type elapsed_time: int
        :param meta_info: The meta_info of this State.  # noqa: E501
        :type meta_info: MetaInfo
        :param scenario_complete: The scenario_complete of this State.  # noqa: E501
        :type scenario_complete: bool
        :param mission: The mission of this State.  # noqa: E501
        :type mission: Mission
        :param environment: The environment of this State.  # noqa: E501
        :type environment: Environment
        :param threat_state: The threat_state of this State.  # noqa: E501
        :type threat_state: ThreatState
        :param supplies: The supplies of this State.  # noqa: E501
        :type supplies: List[Supplies]
        :param characters: The characters of this State.  # noqa: E501
        :type characters: List[Character]
        """
        self.swagger_types = {
            'unstructured': str,
            'elapsed_time': int,
            'meta_info': MetaInfo,
            'scenario_complete': bool,
            'mission': Mission,
            'environment': Environment,
            'threat_state': ThreatState,
            'supplies': List[Supplies],
            'characters': List[Character]
        }

        self.attribute_map = {
            'unstructured': 'unstructured',
            'elapsed_time': 'elapsed_time',
            'meta_info': 'meta_info',
            'scenario_complete': 'scenario_complete',
            'mission': 'mission',
            'environment': 'environment',
            'threat_state': 'threat_state',
            'supplies': 'supplies',
            'characters': 'characters'
        }
        self._unstructured = unstructured
        self._elapsed_time = elapsed_time
        self._meta_info = meta_info
        self._scenario_complete = scenario_complete
        self._mission = mission
        self._environment = environment
        self._threat_state = threat_state
        self._supplies = supplies
        self._characters = characters

    @classmethod
    def from_dict(cls, dikt) -> 'State':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The State of this State.  # noqa: E501
        :rtype: State
        """
        return util.deserialize_model(dikt, cls)

    @property
    def unstructured(self) -> str:
        """Gets the unstructured of this State.

        Natural language, plain text description of a scene's state  # noqa: E501

        :return: The unstructured of this State.
        :rtype: str
        """
        return self._unstructured

    @unstructured.setter
    def unstructured(self, unstructured: str):
        """Sets the unstructured of this State.

        Natural language, plain text description of a scene's state  # noqa: E501

        :param unstructured: The unstructured of this State.
        :type unstructured: str
        """
        if unstructured is None:
            raise ValueError("Invalid value for `unstructured`, must not be `None`")  # noqa: E501

        self._unstructured = unstructured

    @property
    def elapsed_time(self) -> int:
        """Gets the elapsed_time of this State.

        The simulated elapsed time (in seconds) since the scenario started  # noqa: E501

        :return: The elapsed_time of this State.
        :rtype: int
        """
        return self._elapsed_time

    @elapsed_time.setter
    def elapsed_time(self, elapsed_time: int):
        """Sets the elapsed_time of this State.

        The simulated elapsed time (in seconds) since the scenario started  # noqa: E501

        :param elapsed_time: The elapsed_time of this State.
        :type elapsed_time: int
        """

        self._elapsed_time = elapsed_time

    @property
    def meta_info(self) -> MetaInfo:
        """Gets the meta_info of this State.


        :return: The meta_info of this State.
        :rtype: MetaInfo
        """
        return self._meta_info

    @meta_info.setter
    def meta_info(self, meta_info: MetaInfo):
        """Sets the meta_info of this State.


        :param meta_info: The meta_info of this State.
        :type meta_info: MetaInfo
        """

        self._meta_info = meta_info

    @property
    def scenario_complete(self) -> bool:
        """Gets the scenario_complete of this State.

        set to true if the scenario is complete; subsequent calls involving that scenario will return an error code  # noqa: E501

        :return: The scenario_complete of this State.
        :rtype: bool
        """
        return self._scenario_complete

    @scenario_complete.setter
    def scenario_complete(self, scenario_complete: bool):
        """Sets the scenario_complete of this State.

        set to true if the scenario is complete; subsequent calls involving that scenario will return an error code  # noqa: E501

        :param scenario_complete: The scenario_complete of this State.
        :type scenario_complete: bool
        """

        self._scenario_complete = scenario_complete

    @property
    def mission(self) -> Mission:
        """Gets the mission of this State.


        :return: The mission of this State.
        :rtype: Mission
        """
        return self._mission

    @mission.setter
    def mission(self, mission: Mission):
        """Sets the mission of this State.


        :param mission: The mission of this State.
        :type mission: Mission
        """

        self._mission = mission

    @property
    def environment(self) -> Environment:
        """Gets the environment of this State.


        :return: The environment of this State.
        :rtype: Environment
        """
        return self._environment

    @environment.setter
    def environment(self, environment: Environment):
        """Sets the environment of this State.


        :param environment: The environment of this State.
        :type environment: Environment
        """
        if environment is None:
            raise ValueError("Invalid value for `environment`, must not be `None`")  # noqa: E501

        self._environment = environment

    @property
    def threat_state(self) -> ThreatState:
        """Gets the threat_state of this State.


        :return: The threat_state of this State.
        :rtype: ThreatState
        """
        return self._threat_state

    @threat_state.setter
    def threat_state(self, threat_state: ThreatState):
        """Sets the threat_state of this State.


        :param threat_state: The threat_state of this State.
        :type threat_state: ThreatState
        """

        self._threat_state = threat_state

    @property
    def supplies(self) -> List[Supplies]:
        """Gets the supplies of this State.

        A list of supplies available to the medic  # noqa: E501

        :return: The supplies of this State.
        :rtype: List[Supplies]
        """
        return self._supplies

    @supplies.setter
    def supplies(self, supplies: List[Supplies]):
        """Sets the supplies of this State.

        A list of supplies available to the medic  # noqa: E501

        :param supplies: The supplies of this State.
        :type supplies: List[Supplies]
        """
        if supplies is None:
            raise ValueError("Invalid value for `supplies`, must not be `None`")  # noqa: E501

        self._supplies = supplies

    @property
    def characters(self) -> List[Character]:
        """Gets the characters of this State.

        A list of characters in the scene, including injured patients, civilians, medics, etc.  # noqa: E501

        :return: The characters of this State.
        :rtype: List[Character]
        """
        return self._characters

    @characters.setter
    def characters(self, characters: List[Character]):
        """Sets the characters of this State.

        A list of characters in the scene, including injured patients, civilians, medics, etc.  # noqa: E501

        :param characters: The characters of this State.
        :type characters: List[Character]
        """
        if characters is None:
            raise ValueError("Invalid value for `characters`, must not be `None`")  # noqa: E501

        self._characters = characters
