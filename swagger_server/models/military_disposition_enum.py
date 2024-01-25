# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server import util


class MilitaryDispositionEnum(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """

    """
    allowed enum values
    """
    ALLIED_US = "Allied US"
    ALLIED = "Allied"
    CIVILIAN = "Civilian"
    MILITARY_ADVERSARY = "Military Adversary"
    MILITARY_NEUTRAL = "Military Neutral"
    NON_MILITARY_ADVERSARY = "Non-Military Adversary"
    def __init__(self):  # noqa: E501
        """MilitaryDispositionEnum - a model defined in Swagger

        """
        self.swagger_types = {
        }

        self.attribute_map = {
        }

    @classmethod
    def from_dict(cls, dikt) -> 'MilitaryDispositionEnum':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The MilitaryDispositionEnum of this MilitaryDispositionEnum.  # noqa: E501
        :rtype: MilitaryDispositionEnum
        """
        return util.deserialize_model(dikt, cls)
