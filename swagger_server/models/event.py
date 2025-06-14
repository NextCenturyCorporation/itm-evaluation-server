from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model import Model
from swagger_server.models.event_type_enum import EventTypeEnum
from swagger_server import util

from swagger_server.models.event_type_enum import EventTypeEnum  # noqa: E501

class Event(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, unstructured=None, type=None, source=None, object=None, when=None, action_id=None, relevant_state=None):  # noqa: E501
        """Event - a model defined in OpenAPI

        :param unstructured: The unstructured of this Event.  # noqa: E501
        :type unstructured: str
        :param type: The type of this Event.  # noqa: E501
        :type type: EventTypeEnum
        :param source: The source of this Event.  # noqa: E501
        :type source: str
        :param object: The object of this Event.  # noqa: E501
        :type object: str
        :param when: The when of this Event.  # noqa: E501
        :type when: float
        :param action_id: The action_id of this Event.  # noqa: E501
        :type action_id: str
        :param relevant_state: The relevant_state of this Event.  # noqa: E501
        :type relevant_state: List[str]
        """
        self.openapi_types = {
            'unstructured': str,
            'type': EventTypeEnum,
            'source': str,
            'object': str,
            'when': float,
            'action_id': str,
            'relevant_state': List[str]
        }

        self.attribute_map = {
            'unstructured': 'unstructured',
            'type': 'type',
            'source': 'source',
            'object': 'object',
            'when': 'when',
            'action_id': 'action_id',
            'relevant_state': 'relevant_state'
        }

        self._unstructured = unstructured
        self._type = type
        self._source = source
        self._object = object
        self._when = when
        self._action_id = action_id
        self._relevant_state = relevant_state

    @classmethod
    def from_dict(cls, dikt) -> 'Event':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Event of this Event.  # noqa: E501
        :rtype: Event
        """
        return util.deserialize_model(dikt, cls)

    @property
    def unstructured(self) -> str:
        """Gets the unstructured of this Event.

        Natural language, plain text description of the event  # noqa: E501

        :return: The unstructured of this Event.
        :rtype: str
        """
        return self._unstructured

    @unstructured.setter
    def unstructured(self, unstructured: str):
        """Sets the unstructured of this Event.

        Natural language, plain text description of the event  # noqa: E501

        :param unstructured: The unstructured of this Event.
        :type unstructured: str
        """
        if unstructured is None:
            raise ValueError("Invalid value for `unstructured`, must not be `None`")  # noqa: E501

        self._unstructured = unstructured

    @property
    def type(self) -> EventTypeEnum:
        """Gets the type of this Event.


        :return: The type of this Event.
        :rtype: EventTypeEnum
        """
        return self._type

    @type.setter
    def type(self, type: EventTypeEnum):
        """Sets the type of this Event.


        :param type: The type of this Event.
        :type type: EventTypeEnum
        """
        if type is None:
            raise ValueError("Invalid value for `type`, must not be `None`")  # noqa: E501

        self._type = type

    @property
    def source(self) -> str:
        """Gets the source of this Event.

        The 'subject' of the event; can be a character `id` or an `EntityTypeEnum`  # noqa: E501

        :return: The source of this Event.
        :rtype: str
        """
        return self._source

    @source.setter
    def source(self, source: str):
        """Sets the source of this Event.

        The 'subject' of the event; can be a character `id` or an `EntityTypeEnum`  # noqa: E501

        :param source: The source of this Event.
        :type source: str
        """

        self._source = source

    @property
    def object(self) -> str:
        """Gets the object of this Event.

        The 'object' of the event; can be a character `id` or an `EntityTypeEnum`  # noqa: E501

        :return: The object of this Event.
        :rtype: str
        """
        return self._object

    @object.setter
    def object(self, object: str):
        """Sets the object of this Event.

        The 'object' of the event; can be a character `id` or an `EntityTypeEnum`  # noqa: E501

        :param object: The object of this Event.
        :type object: str
        """

        self._object = object

    @property
    def when(self) -> float:
        """Gets the when of this Event.

        indicates when (in minutes) the event happened (negative value) or is expected to happen (positive value); omit if zero (event happens now)  # noqa: E501

        :return: The when of this Event.
        :rtype: float
        """
        return self._when

    @when.setter
    def when(self, when: float):
        """Sets the when of this Event.

        indicates when (in minutes) the event happened (negative value) or is expected to happen (positive value); omit if zero (event happens now)  # noqa: E501

        :param when: The when of this Event.
        :type when: float
        """

        self._when = when

    @property
    def action_id(self) -> str:
        """Gets the action_id of this Event.

        An action ID from among the available actions  # noqa: E501

        :return: The action_id of this Event.
        :rtype: str
        """
        return self._action_id

    @action_id.setter
    def action_id(self, action_id: str):
        """Sets the action_id of this Event.

        An action ID from among the available actions  # noqa: E501

        :param action_id: The action_id of this Event.
        :type action_id: str
        """

        self._action_id = action_id

    @property
    def relevant_state(self) -> List[str]:
        """Gets the relevant_state of this Event.

        An array of relevant state for the Event  # noqa: E501

        :return: The relevant_state of this Event.
        :rtype: List[str]
        """
        return self._relevant_state

    @relevant_state.setter
    def relevant_state(self, relevant_state: List[str]):
        """Sets the relevant_state of this Event.

        An array of relevant state for the Event  # noqa: E501

        :param relevant_state: The relevant_state of this Event.
        :type relevant_state: List[str]
        """

        self._relevant_state = relevant_state
