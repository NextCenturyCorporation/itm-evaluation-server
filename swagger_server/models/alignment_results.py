# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.alignment_source import AlignmentSource  # noqa: F401,E501
from swagger_server import util


class AlignmentResults(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, alignment_source: List[AlignmentSource]=None, alignment_target_id: str=None, score: float=None):  # noqa: E501
        """AlignmentResults - a model defined in Swagger

        :param alignment_source: The alignment_source of this AlignmentResults.  # noqa: E501
        :type alignment_source: List[AlignmentSource]
        :param alignment_target_id: The alignment_target_id of this AlignmentResults.  # noqa: E501
        :type alignment_target_id: str
        :param score: The score of this AlignmentResults.  # noqa: E501
        :type score: float
        """
        self.swagger_types = {
            'alignment_source': List[AlignmentSource],
            'alignment_target_id': str,
            'score': float
        }

        self.attribute_map = {
            'alignment_source': 'alignment_source',
            'alignment_target_id': 'alignment_target_id',
            'score': 'score'
        }
        self._alignment_source = alignment_source
        self._alignment_target_id = alignment_target_id
        self._score = score

    @classmethod
    def from_dict(cls, dikt) -> 'AlignmentResults':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The AlignmentResults of this AlignmentResults.  # noqa: E501
        :rtype: AlignmentResults
        """
        return util.deserialize_model(dikt, cls)

    @property
    def alignment_source(self) -> List[AlignmentSource]:
        """Gets the alignment_source of this AlignmentResults.


        :return: The alignment_source of this AlignmentResults.
        :rtype: List[AlignmentSource]
        """
        return self._alignment_source

    @alignment_source.setter
    def alignment_source(self, alignment_source: List[AlignmentSource]):
        """Sets the alignment_source of this AlignmentResults.


        :param alignment_source: The alignment_source of this AlignmentResults.
        :type alignment_source: List[AlignmentSource]
        """
        if alignment_source is None:
            raise ValueError("Invalid value for `alignment_source`, must not be `None`")  # noqa: E501

        self._alignment_source = alignment_source

    @property
    def alignment_target_id(self) -> str:
        """Gets the alignment_target_id of this AlignmentResults.

        ID of desired profile to align responses to.  # noqa: E501

        :return: The alignment_target_id of this AlignmentResults.
        :rtype: str
        """
        return self._alignment_target_id

    @alignment_target_id.setter
    def alignment_target_id(self, alignment_target_id: str):
        """Sets the alignment_target_id of this AlignmentResults.

        ID of desired profile to align responses to.  # noqa: E501

        :param alignment_target_id: The alignment_target_id of this AlignmentResults.
        :type alignment_target_id: str
        """
        if alignment_target_id is None:
            raise ValueError("Invalid value for `alignment_target_id`, must not be `None`")  # noqa: E501

        self._alignment_target_id = alignment_target_id

    @property
    def score(self) -> float:
        """Gets the score of this AlignmentResults.

        Measured alignment, 0 (completely unaligned) - 1 (completely aligned).  # noqa: E501

        :return: The score of this AlignmentResults.
        :rtype: float
        """
        return self._score

    @score.setter
    def score(self, score: float):
        """Sets the score of this AlignmentResults.

        Measured alignment, 0 (completely unaligned) - 1 (completely aligned).  # noqa: E501

        :param score: The score of this AlignmentResults.
        :type score: float
        """
        if score is None:
            raise ValueError("Invalid value for `score`, must not be `None`")  # noqa: E501

        self._score = score
