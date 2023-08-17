# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class Action(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, scenario_id: str=None, action_type: str=None, casualty_id: str=None, unstructured: str=None, justification: str=None, parameters: List[Dict[str, str]]=None):  # noqa: E501
        """Action - a model defined in Swagger

        :param scenario_id: The scenario_id of this Action.  # noqa: E501
        :type scenario_id: str
        :param action_type: The action_type of this Action.  # noqa: E501
        :type action_type: str
        :param casualty_id: The casualty_id of this Action.  # noqa: E501
        :type casualty_id: str
        :param unstructured: The unstructured of this Action.  # noqa: E501
        :type unstructured: str
        :param justification: The justification of this Action.  # noqa: E501
        :type justification: str
        :param parameters: The parameters of this Action.  # noqa: E501
        :type parameters: List[Dict[str, str]]
        """
        self.swagger_types = {
            'scenario_id': str,
            'action_type': str,
            'casualty_id': str,
            'unstructured': str,
            'justification': str,
            'parameters': List[Dict[str, str]]
        }

        self.attribute_map = {
            'scenario_id': 'scenario_id',
            'action_type': 'action_type',
            'casualty_id': 'casualty_id',
            'unstructured': 'unstructured',
            'justification': 'justification',
            'parameters': 'parameters'
        }
        self._scenario_id = scenario_id
        self._action_type = action_type
        self._casualty_id = casualty_id
        self._unstructured = unstructured
        self._justification = justification
        self._parameters = parameters

    @classmethod
    def from_dict(cls, dikt) -> 'Action':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Action of this Action.  # noqa: E501
        :rtype: Action
        """
        return util.deserialize_model(dikt, cls)

    @property
    def scenario_id(self) -> str:
        """Gets the scenario_id of this Action.

        scenario ID this probe is for  # noqa: E501

        :return: The scenario_id of this Action.
        :rtype: str
        """
        return self._scenario_id

    @scenario_id.setter
    def scenario_id(self, scenario_id: str):
        """Sets the scenario_id of this Action.

        scenario ID this probe is for  # noqa: E501

        :param scenario_id: The scenario_id of this Action.
        :type scenario_id: str
        """
        if scenario_id is None:
            raise ValueError("Invalid value for `scenario_id`, must not be `None`")  # noqa: E501

        self._scenario_id = scenario_id

    @property
    def action_type(self) -> str:
        """Gets the action_type of this Action.

        The action type taken from a controlled vocabulary.  # noqa: E501

        :return: The action_type of this Action.
        :rtype: str
        """
        return self._action_type

    @action_type.setter
    def action_type(self, action_type: str):
        """Sets the action_type of this Action.

        The action type taken from a controlled vocabulary.  # noqa: E501

        :param action_type: The action_type of this Action.
        :type action_type: str
        """
        allowed_values = ["APPLY_TREATMENT", "DIRECT_MOBILE_CASUALTIES", "CHECK_ALL_VITALS", "CHECK_PULSE", "CHECK_RESPIRATION", "SITREP", "TAG_CASUALTY"]  # noqa: E501
        if action_type not in allowed_values:
            raise ValueError(
                "Invalid value for `action_type` ({0}), must be one of {1}"
                .format(action_type, allowed_values)
            )

        self._action_type = action_type

    @property
    def casualty_id(self) -> str:
        """Gets the casualty_id of this Action.

        The ID of the casualty being acted upon  # noqa: E501

        :return: The casualty_id of this Action.
        :rtype: str
        """
        return self._casualty_id

    @casualty_id.setter
    def casualty_id(self, casualty_id: str):
        """Sets the casualty_id of this Action.

        The ID of the casualty being acted upon  # noqa: E501

        :param casualty_id: The casualty_id of this Action.
        :type casualty_id: str
        """

        self._casualty_id = casualty_id

    @property
    def unstructured(self) -> str:
        """Gets the unstructured of this Action.

        a plain text unstructured description of the action  # noqa: E501

        :return: The unstructured of this Action.
        :rtype: str
        """
        return self._unstructured

    @unstructured.setter
    def unstructured(self, unstructured: str):
        """Sets the unstructured of this Action.

        a plain text unstructured description of the action  # noqa: E501

        :param unstructured: The unstructured of this Action.
        :type unstructured: str
        """

        self._unstructured = unstructured

    @property
    def justification(self) -> str:
        """Gets the justification of this Action.

        A justification of the action taken  # noqa: E501

        :return: The justification of this Action.
        :rtype: str
        """
        return self._justification

    @justification.setter
    def justification(self, justification: str):
        """Sets the justification of this Action.

        A justification of the action taken  # noqa: E501

        :param justification: The justification of this Action.
        :type justification: str
        """

        self._justification = justification

    @property
    def parameters(self) -> List[Dict[str, str]]:
        """Gets the parameters of this Action.

        an array of action-specific parameters  # noqa: E501

        :return: The parameters of this Action.
        :rtype: List[Dict[str, str]]
        """
        return self._parameters

    @parameters.setter
    def parameters(self, parameters: List[Dict[str, str]]):
        """Sets the parameters of this Action.

        an array of action-specific parameters  # noqa: E501

        :param parameters: The parameters of this Action.
        :type parameters: List[Dict[str, str]]
        """

        self._parameters = parameters