from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model import Model
from swagger_server import util


class CharacterRoleEnum(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    """
    allowed enum values
    """
    NOT_SPECIFIED = 'Not specified'
    def __init__(self):  # noqa: E501
        """CharacterRoleEnum - a model defined in OpenAPI

        """
        self.openapi_types = {
        }

        self.attribute_map = {
        }

    @classmethod
    def from_dict(cls, dikt) -> 'CharacterRoleEnum':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The CharacterRoleEnum of this CharacterRoleEnum.  # noqa: E501
        :rtype: CharacterRoleEnum
        """
        return util.deserialize_model(dikt, cls)
