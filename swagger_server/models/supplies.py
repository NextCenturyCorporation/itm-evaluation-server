# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.supply_type_enum import SupplyTypeEnum  # noqa: F401,E501
from swagger_server import util


class Supplies(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, type: SupplyTypeEnum=None, reusable: bool=False, quantity: int=None):  # noqa: E501
        """Supplies - a model defined in Swagger

        :param type: The type of this Supplies.  # noqa: E501
        :type type: SupplyTypeEnum
        :param reusable: The reusable of this Supplies.  # noqa: E501
        :type reusable: bool
        :param quantity: The quantity of this Supplies.  # noqa: E501
        :type quantity: int
        """
        self.swagger_types = {
            'type': SupplyTypeEnum,
            'reusable': bool,
            'quantity': int
        }

        self.attribute_map = {
            'type': 'type',
            'reusable': 'reusable',
            'quantity': 'quantity'
        }
        self._type = type
        self._reusable = reusable
        self._quantity = quantity

    @classmethod
    def from_dict(cls, dikt) -> 'Supplies':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Supplies of this Supplies.  # noqa: E501
        :rtype: Supplies
        """
        return util.deserialize_model(dikt, cls)

    @property
    def type(self) -> SupplyTypeEnum:
        """Gets the type of this Supplies.


        :return: The type of this Supplies.
        :rtype: SupplyTypeEnum
        """
        return self._type

    @type.setter
    def type(self, type: SupplyTypeEnum):
        """Sets the type of this Supplies.


        :param type: The type of this Supplies.
        :type type: SupplyTypeEnum
        """
        if type is None:
            raise ValueError("Invalid value for `type`, must not be `None`")  # noqa: E501

        self._type = type

    @property
    def reusable(self) -> bool:
        """Gets the reusable of this Supplies.

        Whether or not item is consumable/reusable  # noqa: E501

        :return: The reusable of this Supplies.
        :rtype: bool
        """
        return self._reusable

    @reusable.setter
    def reusable(self, reusable: bool):
        """Sets the reusable of this Supplies.

        Whether or not item is consumable/reusable  # noqa: E501

        :param reusable: The reusable of this Supplies.
        :type reusable: bool
        """

        self._reusable = reusable

    @property
    def quantity(self) -> int:
        """Gets the quantity of this Supplies.

        Number of items available in the medical bag  # noqa: E501

        :return: The quantity of this Supplies.
        :rtype: int
        """
        return self._quantity

    @quantity.setter
    def quantity(self, quantity: int):
        """Sets the quantity of this Supplies.

        Number of items available in the medical bag  # noqa: E501

        :param quantity: The quantity of this Supplies.
        :type quantity: int
        """
        if quantity is None:
            raise ValueError("Invalid value for `quantity`, must not be `None`")  # noqa: E501

        self._quantity = quantity
