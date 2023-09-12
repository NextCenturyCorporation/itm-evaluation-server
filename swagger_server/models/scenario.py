# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.state import State  # noqa: F401,E501
from swagger_server.models.triage_category import TriageCategory  # noqa: F401,E501
from swagger_server import util


class Scenario(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, id: str='1234', name: str=None, session_complete: bool=None, start_time: str=None, state: State=None, triage_categories: List[TriageCategory]=None):  # noqa: E501
        """Scenario - a model defined in Swagger

        :param id: The id of this Scenario.  # noqa: E501
        :type id: str
        :param name: The name of this Scenario.  # noqa: E501
        :type name: str
        :param session_complete: The session_complete of this Scenario.  # noqa: E501
        :type session_complete: bool
        :param start_time: The start_time of this Scenario.  # noqa: E501
        :type start_time: str
        :param state: The state of this Scenario.  # noqa: E501
        :type state: State
        :param triage_categories: The triage_categories of this Scenario.  # noqa: E501
        :type triage_categories: List[TriageCategory]
        """
        self.swagger_types = {
            'id': str,
            'name': str,
            'session_complete': bool,
            'start_time': str,
            'state': State,
            'triage_categories': List[TriageCategory]
        }

        self.attribute_map = {
            'id': 'id',
            'name': 'name',
            'session_complete': 'session_complete',
            'start_time': 'start_time',
            'state': 'state',
            'triage_categories': 'triage_categories'
        }
        self._id = id
        self._name = name
        self._session_complete = session_complete
        self._start_time = start_time
        self._state = state
        self._triage_categories = triage_categories

    @classmethod
    def from_dict(cls, dikt) -> 'Scenario':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Scenario of this Scenario.  # noqa: E501
        :rtype: Scenario
        """
        return util.deserialize_model(dikt, cls)

    @property
    def id(self) -> str:
        """Gets the id of this Scenario.

        a globally unique id for the scenario  # noqa: E501

        :return: The id of this Scenario.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id: str):
        """Sets the id of this Scenario.

        a globally unique id for the scenario  # noqa: E501

        :param id: The id of this Scenario.
        :type id: str
        """
        if id is None:
            raise ValueError("Invalid value for `id`, must not be `None`")  # noqa: E501

        self._id = id

    @property
    def name(self) -> str:
        """Gets the name of this Scenario.

        human-readable scenario name, not necessarily unique  # noqa: E501

        :return: The name of this Scenario.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """Sets the name of this Scenario.

        human-readable scenario name, not necessarily unique  # noqa: E501

        :param name: The name of this Scenario.
        :type name: str
        """
        if name is None:
            raise ValueError("Invalid value for `name`, must not be `None`")  # noqa: E501

        self._name = name

    @property
    def session_complete(self) -> bool:
        """Gets the session_complete of this Scenario.

        set to true if the session is complete; that is, there are no more scenarios  # noqa: E501

        :return: The session_complete of this Scenario.
        :rtype: bool
        """
        return self._session_complete

    @session_complete.setter
    def session_complete(self, session_complete: bool):
        """Sets the session_complete of this Scenario.

        set to true if the session is complete; that is, there are no more scenarios  # noqa: E501

        :param session_complete: The session_complete of this Scenario.
        :type session_complete: bool
        """

        self._session_complete = session_complete

    @property
    def start_time(self) -> str:
        """Gets the start_time of this Scenario.

        the wall clock local start time of the scenario, expressed as hh:mm  # noqa: E501

        :return: The start_time of this Scenario.
        :rtype: str
        """
        return self._start_time

    @start_time.setter
    def start_time(self, start_time: str):
        """Sets the start_time of this Scenario.

        the wall clock local start time of the scenario, expressed as hh:mm  # noqa: E501

        :param start_time: The start_time of this Scenario.
        :type start_time: str
        """

        self._start_time = start_time

    @property
    def state(self) -> State:
        """Gets the state of this Scenario.


        :return: The state of this Scenario.
        :rtype: State
        """
        return self._state

    @state.setter
    def state(self, state: State):
        """Sets the state of this Scenario.


        :param state: The state of this Scenario.
        :type state: State
        """

        self._state = state

    @property
    def triage_categories(self) -> List[TriageCategory]:
        """Gets the triage_categories of this Scenario.


        :return: The triage_categories of this Scenario.
        :rtype: List[TriageCategory]
        """
        return self._triage_categories

    @triage_categories.setter
    def triage_categories(self, triage_categories: List[TriageCategory]):
        """Sets the triage_categories of this Scenario.


        :param triage_categories: The triage_categories of this Scenario.
        :type triage_categories: List[TriageCategory]
        """

        self._triage_categories = triage_categories
