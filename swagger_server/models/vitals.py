# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.vitals_breathing import VitalsBreathing  # noqa: F401,E501
from swagger_server.models.vitals_mental_status import VitalsMentalStatus  # noqa: F401,E501
from swagger_server import util


class Vitals(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, conscious: bool=None, mental_status: VitalsMentalStatus=None, breathing: VitalsBreathing=None, hrpmin: int=None):  # noqa: E501
        """Vitals - a model defined in Swagger

        :param conscious: The conscious of this Vitals.  # noqa: E501
        :type conscious: bool
        :param mental_status: The mental_status of this Vitals.  # noqa: E501
        :type mental_status: VitalsMentalStatus
        :param breathing: The breathing of this Vitals.  # noqa: E501
        :type breathing: VitalsBreathing
        :param hrpmin: The hrpmin of this Vitals.  # noqa: E501
        :type hrpmin: int
        """
        self.swagger_types = {
            'conscious': bool,
            'mental_status': VitalsMentalStatus,
            'breathing': VitalsBreathing,
            'hrpmin': int
        }

        self.attribute_map = {
            'conscious': 'conscious',
            'mental_status': 'mental_status',
            'breathing': 'breathing',
            'hrpmin': 'hrpmin'
        }
        self._conscious = conscious
        self._mental_status = mental_status
        self._breathing = breathing
        self._hrpmin = hrpmin

    @classmethod
    def from_dict(cls, dikt) -> 'Vitals':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Vitals of this Vitals.  # noqa: E501
        :rtype: Vitals
        """
        return util.deserialize_model(dikt, cls)

    @property
    def conscious(self) -> bool:
        """Gets the conscious of this Vitals.

        whether or not the character is conscious  # noqa: E501

        :return: The conscious of this Vitals.
        :rtype: bool
        """
        return self._conscious

    @conscious.setter
    def conscious(self, conscious: bool):
        """Sets the conscious of this Vitals.

        whether or not the character is conscious  # noqa: E501

        :param conscious: The conscious of this Vitals.
        :type conscious: bool
        """

        self._conscious = conscious

    @property
    def mental_status(self) -> VitalsMentalStatus:
        """Gets the mental_status of this Vitals.


        :return: The mental_status of this Vitals.
        :rtype: VitalsMentalStatus
        """
        return self._mental_status

    @mental_status.setter
    def mental_status(self, mental_status: VitalsMentalStatus):
        """Sets the mental_status of this Vitals.


        :param mental_status: The mental_status of this Vitals.
        :type mental_status: VitalsMentalStatus
        """

        self._mental_status = mental_status

    @property
    def breathing(self) -> VitalsBreathing:
        """Gets the breathing of this Vitals.


        :return: The breathing of this Vitals.
        :rtype: VitalsBreathing
        """
        return self._breathing

    @breathing.setter
    def breathing(self, breathing: VitalsBreathing):
        """Sets the breathing of this Vitals.


        :param breathing: The breathing of this Vitals.
        :type breathing: VitalsBreathing
        """

        self._breathing = breathing

    @property
    def hrpmin(self) -> int:
        """Gets the hrpmin of this Vitals.

        heart rate in beats per minute  # noqa: E501

        :return: The hrpmin of this Vitals.
        :rtype: int
        """
        return self._hrpmin

    @hrpmin.setter
    def hrpmin(self, hrpmin: int):
        """Sets the hrpmin of this Vitals.

        heart rate in beats per minute  # noqa: E501

        :param hrpmin: The hrpmin of this Vitals.
        :type hrpmin: int
        """

        self._hrpmin = hrpmin
