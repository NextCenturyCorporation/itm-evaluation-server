# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class ProbeResponses(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, character_id: str=None, probe_id: str=None, minimal: str=None, delayed: str=None, immediate: str=None, expectant: str=None):  # noqa: E501
        """ProbeResponses - a model defined in Swagger

        :param character_id: The character_id of this ProbeResponses.  # noqa: E501
        :type character_id: str
        :param probe_id: The probe_id of this ProbeResponses.  # noqa: E501
        :type probe_id: str
        :param minimal: The minimal of this ProbeResponses.  # noqa: E501
        :type minimal: str
        :param delayed: The delayed of this ProbeResponses.  # noqa: E501
        :type delayed: str
        :param immediate: The immediate of this ProbeResponses.  # noqa: E501
        :type immediate: str
        :param expectant: The expectant of this ProbeResponses.  # noqa: E501
        :type expectant: str
        """
        self.swagger_types = {
            'character_id': str,
            'probe_id': str,
            'minimal': str,
            'delayed': str,
            'immediate': str,
            'expectant': str
        }

        self.attribute_map = {
            'character_id': 'character_id',
            'probe_id': 'probe_id',
            'minimal': 'minimal',
            'delayed': 'delayed',
            'immediate': 'immediate',
            'expectant': 'expectant'
        }
        self._character_id = character_id
        self._probe_id = probe_id
        self._minimal = minimal
        self._delayed = delayed
        self._immediate = immediate
        self._expectant = expectant

    @classmethod
    def from_dict(cls, dikt) -> 'ProbeResponses':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The ProbeResponses of this ProbeResponses.  # noqa: E501
        :rtype: ProbeResponses
        """
        return util.deserialize_model(dikt, cls)

    @property
    def character_id(self) -> str:
        """Gets the character_id of this ProbeResponses.

        A valid character ID from the scene  # noqa: E501

        :return: The character_id of this ProbeResponses.
        :rtype: str
        """
        return self._character_id

    @character_id.setter
    def character_id(self, character_id: str):
        """Sets the character_id of this ProbeResponses.

        A valid character ID from the scene  # noqa: E501

        :param character_id: The character_id of this ProbeResponses.
        :type character_id: str
        """
        if character_id is None:
            raise ValueError("Invalid value for `character_id`, must not be `None`")  # noqa: E501

        self._character_id = character_id

    @property
    def probe_id(self) -> str:
        """Gets the probe_id of this ProbeResponses.

        A valid probe_id from the appropriate TA1  # noqa: E501

        :return: The probe_id of this ProbeResponses.
        :rtype: str
        """
        return self._probe_id

    @probe_id.setter
    def probe_id(self, probe_id: str):
        """Sets the probe_id of this ProbeResponses.

        A valid probe_id from the appropriate TA1  # noqa: E501

        :param probe_id: The probe_id of this ProbeResponses.
        :type probe_id: str
        """
        if probe_id is None:
            raise ValueError("Invalid value for `probe_id`, must not be `None`")  # noqa: E501

        self._probe_id = probe_id

    @property
    def minimal(self) -> str:
        """Gets the minimal of this ProbeResponses.

        The probe response to send for a MINIMAL tag  # noqa: E501

        :return: The minimal of this ProbeResponses.
        :rtype: str
        """
        return self._minimal

    @minimal.setter
    def minimal(self, minimal: str):
        """Sets the minimal of this ProbeResponses.

        The probe response to send for a MINIMAL tag  # noqa: E501

        :param minimal: The minimal of this ProbeResponses.
        :type minimal: str
        """
        if minimal is None:
            raise ValueError("Invalid value for `minimal`, must not be `None`")  # noqa: E501

        self._minimal = minimal

    @property
    def delayed(self) -> str:
        """Gets the delayed of this ProbeResponses.

        The probe response to send for a DELAYED tag  # noqa: E501

        :return: The delayed of this ProbeResponses.
        :rtype: str
        """
        return self._delayed

    @delayed.setter
    def delayed(self, delayed: str):
        """Sets the delayed of this ProbeResponses.

        The probe response to send for a DELAYED tag  # noqa: E501

        :param delayed: The delayed of this ProbeResponses.
        :type delayed: str
        """
        if delayed is None:
            raise ValueError("Invalid value for `delayed`, must not be `None`")  # noqa: E501

        self._delayed = delayed

    @property
    def immediate(self) -> str:
        """Gets the immediate of this ProbeResponses.

        The probe response to send for a IMMEDIATE tag  # noqa: E501

        :return: The immediate of this ProbeResponses.
        :rtype: str
        """
        return self._immediate

    @immediate.setter
    def immediate(self, immediate: str):
        """Sets the immediate of this ProbeResponses.

        The probe response to send for a IMMEDIATE tag  # noqa: E501

        :param immediate: The immediate of this ProbeResponses.
        :type immediate: str
        """
        if immediate is None:
            raise ValueError("Invalid value for `immediate`, must not be `None`")  # noqa: E501

        self._immediate = immediate

    @property
    def expectant(self) -> str:
        """Gets the expectant of this ProbeResponses.

        The probe response to send for a EXPECTANT tag  # noqa: E501

        :return: The expectant of this ProbeResponses.
        :rtype: str
        """
        return self._expectant

    @expectant.setter
    def expectant(self, expectant: str):
        """Sets the expectant of this ProbeResponses.

        The probe response to send for a EXPECTANT tag  # noqa: E501

        :param expectant: The expectant of this ProbeResponses.
        :type expectant: str
        """
        if expectant is None:
            raise ValueError("Invalid value for `expectant`, must not be `None`")  # noqa: E501

        self._expectant = expectant
