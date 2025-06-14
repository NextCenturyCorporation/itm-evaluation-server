from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model import Model
from swagger_server.models.demographics import Demographics
from swagger_server.models.rapport_enum import RapportEnum
from swagger_server import util

from swagger_server.models.demographics import Demographics  # noqa: E501
from swagger_server.models.rapport_enum import RapportEnum  # noqa: E501

class Character(Model):
    """NOTE: This class is auto generated by OpenAPI Generator (https://openapi-generator.tech).

    Do not edit the class manually.
    """

    def __init__(self, medical_condition=None, attribute_rating=None, id=None, name=None, unstructured=None, demographics=None, rapport=None, unseen=False):  # noqa: E501
        """Character - a model defined in OpenAPI

        :param medical_condition: The medical_condition of this Character.  # noqa: E501
        :type medical_condition: float
        :param attribute_rating: The attribute_rating of this Character.  # noqa: E501
        :type attribute_rating: float
        :param id: The id of this Character.  # noqa: E501
        :type id: str
        :param name: The name of this Character.  # noqa: E501
        :type name: str
        :param unstructured: The unstructured of this Character.  # noqa: E501
        :type unstructured: str
        :param demographics: The demographics of this Character.  # noqa: E501
        :type demographics: Demographics
        :param rapport: The rapport of this Character.  # noqa: E501
        :type rapport: RapportEnum
        :param unseen: The unseen of this Character.  # noqa: E501
        :type unseen: bool
        """
        self.openapi_types = {
            'medical_condition': float,
            'attribute_rating': float,
            'id': str,
            'name': str,
            'unstructured': str,
            'demographics': Demographics,
            'rapport': RapportEnum,
            'unseen': bool
        }

        self.attribute_map = {
            'medical_condition': 'medical_condition',
            'attribute_rating': 'attribute_rating',
            'id': 'id',
            'name': 'name',
            'unstructured': 'unstructured',
            'demographics': 'demographics',
            'rapport': 'rapport',
            'unseen': 'unseen'
        }

        self._medical_condition = medical_condition
        self._attribute_rating = attribute_rating
        self._id = id
        self._name = name
        self._unstructured = unstructured
        self._demographics = demographics
        self._rapport = rapport
        self._unseen = unseen

    @classmethod
    def from_dict(cls, dikt) -> 'Character':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The Character of this Character.  # noqa: E501
        :rtype: Character
        """
        return util.deserialize_model(dikt, cls)

    @property
    def medical_condition(self) -> float:
        """Gets the medical_condition of this Character.

        The treatment priority/urgency of a patient's medical condition, 0-1 scale  # noqa: E501

        :return: The medical_condition of this Character.
        :rtype: float
        """
        return self._medical_condition

    @medical_condition.setter
    def medical_condition(self, medical_condition: float):
        """Sets the medical_condition of this Character.

        The treatment priority/urgency of a patient's medical condition, 0-1 scale  # noqa: E501

        :param medical_condition: The medical_condition of this Character.
        :type medical_condition: float
        """
        if medical_condition is not None and medical_condition > 1.0:  # noqa: E501
            raise ValueError("Invalid value for `medical_condition`, must be a value less than or equal to `1.0`")  # noqa: E501
        if medical_condition is not None and medical_condition < 0.0:  # noqa: E501
            raise ValueError("Invalid value for `medical_condition`, must be a value greater than or equal to `0.0`")  # noqa: E501

        self._medical_condition = medical_condition

    @property
    def attribute_rating(self) -> float:
        """Gets the attribute_rating of this Character.

        A scenario-specific characteristic of the patient or situation regarding the patient, 0-1 scale:   Merit Focus (MF): degree of blame for a patient: 0.0 doesn't consider merit when deciding who to treat / always treats the medically favored patient; 1.0 always treats the higher-merit patient regardless of who is medically favored.   Affiliation Focus (AF): degree of closeness for a patient: 0.0 doesn't consider affiliation / always treats the medically favored patient; 1.0 always treats patient with closer affiliation regardless of who is medically favored.   Search vs. Stay (SS): urgency to search for/treat a patient: 0.0 always stays despite how urgent the need is to treat patient in next room; 1.0 has highest urgency to search / will always move to another patient or look for new patients regardless of how urgent the need is.   Personal Safety Focus (PS): amount of danger to reach a patient: 0.0 doesn't consider personal safety and always switches to the medically favored patient; 1.0 won't risk personal safety / always stays in safest place regardless of who is medically favored.   # noqa: E501

        :return: The attribute_rating of this Character.
        :rtype: float
        """
        return self._attribute_rating

    @attribute_rating.setter
    def attribute_rating(self, attribute_rating: float):
        """Sets the attribute_rating of this Character.

        A scenario-specific characteristic of the patient or situation regarding the patient, 0-1 scale:   Merit Focus (MF): degree of blame for a patient: 0.0 doesn't consider merit when deciding who to treat / always treats the medically favored patient; 1.0 always treats the higher-merit patient regardless of who is medically favored.   Affiliation Focus (AF): degree of closeness for a patient: 0.0 doesn't consider affiliation / always treats the medically favored patient; 1.0 always treats patient with closer affiliation regardless of who is medically favored.   Search vs. Stay (SS): urgency to search for/treat a patient: 0.0 always stays despite how urgent the need is to treat patient in next room; 1.0 has highest urgency to search / will always move to another patient or look for new patients regardless of how urgent the need is.   Personal Safety Focus (PS): amount of danger to reach a patient: 0.0 doesn't consider personal safety and always switches to the medically favored patient; 1.0 won't risk personal safety / always stays in safest place regardless of who is medically favored.   # noqa: E501

        :param attribute_rating: The attribute_rating of this Character.
        :type attribute_rating: float
        """
        if attribute_rating is not None and attribute_rating > 1.0:  # noqa: E501
            raise ValueError("Invalid value for `attribute_rating`, must be a value less than or equal to `1.0`")  # noqa: E501
        if attribute_rating is not None and attribute_rating < 0.0:  # noqa: E501
            raise ValueError("Invalid value for `attribute_rating`, must be a value greater than or equal to `0.0`")  # noqa: E501

        self._attribute_rating = attribute_rating

    @property
    def id(self) -> str:
        """Gets the id of this Character.

        A unique character ID throughout the scenario  # noqa: E501

        :return: The id of this Character.
        :rtype: str
        """
        return self._id

    @id.setter
    def id(self, id: str):
        """Sets the id of this Character.

        A unique character ID throughout the scenario  # noqa: E501

        :param id: The id of this Character.
        :type id: str
        """
        if id is None:
            raise ValueError("Invalid value for `id`, must not be `None`")  # noqa: E501

        self._id = id

    @property
    def name(self) -> str:
        """Gets the name of this Character.

        display name, as in a dashboard  # noqa: E501

        :return: The name of this Character.
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name: str):
        """Sets the name of this Character.

        display name, as in a dashboard  # noqa: E501

        :param name: The name of this Character.
        :type name: str
        """
        if name is None:
            raise ValueError("Invalid value for `name`, must not be `None`")  # noqa: E501

        self._name = name

    @property
    def unstructured(self) -> str:
        """Gets the unstructured of this Character.

        Natural language, plain text description of the character  # noqa: E501

        :return: The unstructured of this Character.
        :rtype: str
        """
        return self._unstructured

    @unstructured.setter
    def unstructured(self, unstructured: str):
        """Sets the unstructured of this Character.

        Natural language, plain text description of the character  # noqa: E501

        :param unstructured: The unstructured of this Character.
        :type unstructured: str
        """
        if unstructured is None:
            raise ValueError("Invalid value for `unstructured`, must not be `None`")  # noqa: E501

        self._unstructured = unstructured

    @property
    def demographics(self) -> Demographics:
        """Gets the demographics of this Character.


        :return: The demographics of this Character.
        :rtype: Demographics
        """
        return self._demographics

    @demographics.setter
    def demographics(self, demographics: Demographics):
        """Sets the demographics of this Character.


        :param demographics: The demographics of this Character.
        :type demographics: Demographics
        """
        if demographics is None:
            raise ValueError("Invalid value for `demographics`, must not be `None`")  # noqa: E501

        self._demographics = demographics

    @property
    def rapport(self) -> RapportEnum:
        """Gets the rapport of this Character.


        :return: The rapport of this Character.
        :rtype: RapportEnum
        """
        return self._rapport

    @rapport.setter
    def rapport(self, rapport: RapportEnum):
        """Sets the rapport of this Character.


        :param rapport: The rapport of this Character.
        :type rapport: RapportEnum
        """

        self._rapport = rapport

    @property
    def unseen(self) -> bool:
        """Gets the unseen of this Character.

        whether or not this character is visible in the scene or merely heard or reported about from a nearby location  # noqa: E501

        :return: The unseen of this Character.
        :rtype: bool
        """
        return self._unseen

    @unseen.setter
    def unseen(self, unseen: bool):
        """Sets the unseen of this Character.

        whether or not this character is visible in the scene or merely heard or reported about from a nearby location  # noqa: E501

        :param unseen: The unseen of this Character.
        :type unseen: bool
        """

        self._unseen = unseen
