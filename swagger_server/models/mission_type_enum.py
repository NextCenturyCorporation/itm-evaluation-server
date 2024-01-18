# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class MissionTypeEnum(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    """
    allowed enum values
    """
    LISTENING_OBSERVATION = "Listening/Observation"
    DIRECT_ACTION = "Direct Action"
    HOSTAGE_RESCUE = "Hostage rescue"
    ASSET_TRANSPORT = "Asset transport"
    SENSOR_EMPLACEMENT = "Sensor emplacement"
    INTELLIGENCE_GATHERING = "Intelligence gathering"
    CIVIL_AFFAIRS = "Civil affairs"
    TRAINING = "Training"
    SABOTAGE = "Sabotage"
    SECURITY_PATROL = "Security patrol"
    FIRE_SUPPORT = "Fire support"
    NUCLEAR_DETERRENCE = "Nuclear deterrence"
    EXTRACTION = "Extraction"
    UNKNOWN = "Unknown"
    def __init__(self):  # noqa: E501
        """MissionTypeEnum - a model defined in Swagger

        """
        self.swagger_types = {
        }

        self.attribute_map = {
        }

    @classmethod
    def from_dict(cls, dikt) -> 'MissionTypeEnum':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The MissionTypeEnum of this MissionTypeEnum.  # noqa: E501
        :rtype: MissionTypeEnum
        """
        return util.deserialize_model(dikt, cls)
