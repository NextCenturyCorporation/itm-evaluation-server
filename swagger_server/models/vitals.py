# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.avpu_level_enum import AvpuLevelEnum  # noqa: F401,E501
from swagger_server.models.breathing_level_enum import BreathingLevelEnum  # noqa: F401,E501
from swagger_server.models.heart_rate_enum import HeartRateEnum  # noqa: F401,E501
from swagger_server.models.mental_status_enum import MentalStatusEnum  # noqa: F401,E501
from swagger_server import util


class Vitals(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, avpu: AvpuLevelEnum=None, ambulatory: bool=None, mental_status: MentalStatusEnum=None, breathing: BreathingLevelEnum=None, heart_rate: HeartRateEnum=None, spo2: float=None):  # noqa: E501
        """Vitals - a model defined in Swagger

        :param avpu: The avpu of this Vitals.  # noqa: E501
        :type avpu: AvpuLevelEnum
        :param ambulatory: The ambulatory of this Vitals.  # noqa: E501
        :type ambulatory: bool
        :param mental_status: The mental_status of this Vitals.  # noqa: E501
        :type mental_status: MentalStatusEnum
        :param breathing: The breathing of this Vitals.  # noqa: E501
        :type breathing: BreathingLevelEnum
        :param heart_rate: The heart_rate of this Vitals.  # noqa: E501
        :type heart_rate: HeartRateEnum
        :param spo2: The spo2 of this Vitals.  # noqa: E501
        :type spo2: float
        """
        self.swagger_types = {
            'avpu': AvpuLevelEnum,
            'ambulatory': bool,
            'mental_status': MentalStatusEnum,
            'breathing': BreathingLevelEnum,
            'heart_rate': HeartRateEnum,
            'spo2': float
        }

        self.attribute_map = {
            'avpu': 'avpu',
            'ambulatory': 'ambulatory',
            'mental_status': 'mental_status',
            'breathing': 'breathing',
            'heart_rate': 'heart_rate',
            'spo2': 'spo2'
        }
        self._avpu = avpu
        self._ambulatory = ambulatory
        self._mental_status = mental_status
        self._breathing = breathing
        self._heart_rate = heart_rate
        self._spo2 = spo2

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
    def avpu(self) -> AvpuLevelEnum:
        """Gets the avpu of this Vitals.


        :return: The avpu of this Vitals.
        :rtype: AvpuLevelEnum
        """
        return self._avpu

    @avpu.setter
    def avpu(self, avpu: AvpuLevelEnum):
        """Sets the avpu of this Vitals.


        :param avpu: The avpu of this Vitals.
        :type avpu: AvpuLevelEnum
        """

        self._avpu = avpu

    @property
    def ambulatory(self) -> bool:
        """Gets the ambulatory of this Vitals.

        whether or not the character can walk  # noqa: E501

        :return: The ambulatory of this Vitals.
        :rtype: bool
        """
        return self._ambulatory

    @ambulatory.setter
    def ambulatory(self, ambulatory: bool):
        """Sets the ambulatory of this Vitals.

        whether or not the character can walk  # noqa: E501

        :param ambulatory: The ambulatory of this Vitals.
        :type ambulatory: bool
        """

        self._ambulatory = ambulatory

    @property
    def mental_status(self) -> MentalStatusEnum:
        """Gets the mental_status of this Vitals.


        :return: The mental_status of this Vitals.
        :rtype: MentalStatusEnum
        """
        return self._mental_status

    @mental_status.setter
    def mental_status(self, mental_status: MentalStatusEnum):
        """Sets the mental_status of this Vitals.


        :param mental_status: The mental_status of this Vitals.
        :type mental_status: MentalStatusEnum
        """

        self._mental_status = mental_status

    @property
    def breathing(self) -> BreathingLevelEnum:
        """Gets the breathing of this Vitals.


        :return: The breathing of this Vitals.
        :rtype: BreathingLevelEnum
        """
        return self._breathing

    @breathing.setter
    def breathing(self, breathing: BreathingLevelEnum):
        """Sets the breathing of this Vitals.


        :param breathing: The breathing of this Vitals.
        :type breathing: BreathingLevelEnum
        """

        self._breathing = breathing

    @property
    def heart_rate(self) -> HeartRateEnum:
        """Gets the heart_rate of this Vitals.


        :return: The heart_rate of this Vitals.
        :rtype: HeartRateEnum
        """
        return self._heart_rate

    @heart_rate.setter
    def heart_rate(self, heart_rate: HeartRateEnum):
        """Sets the heart_rate of this Vitals.


        :param heart_rate: The heart_rate of this Vitals.
        :type heart_rate: HeartRateEnum
        """

        self._heart_rate = heart_rate

    @property
    def spo2(self) -> float:
        """Gets the spo2 of this Vitals.

        blood oxygen level (percentage)  # noqa: E501

        :return: The spo2 of this Vitals.
        :rtype: float
        """
        return self._spo2

    @spo2.setter
    def spo2(self, spo2: float):
        """Sets the spo2 of this Vitals.

        blood oxygen level (percentage)  # noqa: E501

        :param spo2: The spo2 of this Vitals.
        :type spo2: float
        """

        self._spo2 = spo2
