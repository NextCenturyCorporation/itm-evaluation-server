# coding: utf-8

from __future__ import absolute_import
from datetime import date, datetime  # noqa: F401

from typing import List, Dict  # noqa: F401

from swagger_server.models.base_model_ import Model
from swagger_server.models.ambient_noise_enum import AmbientNoiseEnum  # noqa: F401,E501
from swagger_server.models.fauna_type_enum import FaunaTypeEnum  # noqa: F401,E501
from swagger_server.models.flora_type_enum import FloraTypeEnum  # noqa: F401,E501
from swagger_server.models.lighting_type_enum import LightingTypeEnum  # noqa: F401,E501
from swagger_server.models.peak_noise_enum import PeakNoiseEnum  # noqa: F401,E501
from swagger_server.models.sim_environment_type_enum import SimEnvironmentTypeEnum  # noqa: F401,E501
from swagger_server.models.terrain_type_enum import TerrainTypeEnum  # noqa: F401,E501
from swagger_server.models.visibility_type_enum import VisibilityTypeEnum  # noqa: F401,E501
from swagger_server.models.weather_type_enum import WeatherTypeEnum  # noqa: F401,E501
from swagger_server import util


class SimEnvironment(Model):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    def __init__(self, unstructured: str=None, type: SimEnvironmentTypeEnum=None, weather: WeatherTypeEnum=None, terrain: TerrainTypeEnum=None, flora: FloraTypeEnum=None, fauna: FaunaTypeEnum=None, temperature: float=None, humidity: float=None, lighting: LightingTypeEnum=None, visibility: VisibilityTypeEnum=None, noise_ambient: AmbientNoiseEnum=None, noise_peak: PeakNoiseEnum=None):  # noqa: E501
        """SimEnvironment - a model defined in Swagger

        :param unstructured: The unstructured of this SimEnvironment.  # noqa: E501
        :type unstructured: str
        :param type: The type of this SimEnvironment.  # noqa: E501
        :type type: SimEnvironmentTypeEnum
        :param weather: The weather of this SimEnvironment.  # noqa: E501
        :type weather: WeatherTypeEnum
        :param terrain: The terrain of this SimEnvironment.  # noqa: E501
        :type terrain: TerrainTypeEnum
        :param flora: The flora of this SimEnvironment.  # noqa: E501
        :type flora: FloraTypeEnum
        :param fauna: The fauna of this SimEnvironment.  # noqa: E501
        :type fauna: FaunaTypeEnum
        :param temperature: The temperature of this SimEnvironment.  # noqa: E501
        :type temperature: float
        :param humidity: The humidity of this SimEnvironment.  # noqa: E501
        :type humidity: float
        :param lighting: The lighting of this SimEnvironment.  # noqa: E501
        :type lighting: LightingTypeEnum
        :param visibility: The visibility of this SimEnvironment.  # noqa: E501
        :type visibility: VisibilityTypeEnum
        :param noise_ambient: The noise_ambient of this SimEnvironment.  # noqa: E501
        :type noise_ambient: AmbientNoiseEnum
        :param noise_peak: The noise_peak of this SimEnvironment.  # noqa: E501
        :type noise_peak: PeakNoiseEnum
        """
        self.swagger_types = {
            'unstructured': str,
            'type': SimEnvironmentTypeEnum,
            'weather': WeatherTypeEnum,
            'terrain': TerrainTypeEnum,
            'flora': FloraTypeEnum,
            'fauna': FaunaTypeEnum,
            'temperature': float,
            'humidity': float,
            'lighting': LightingTypeEnum,
            'visibility': VisibilityTypeEnum,
            'noise_ambient': AmbientNoiseEnum,
            'noise_peak': PeakNoiseEnum
        }

        self.attribute_map = {
            'unstructured': 'unstructured',
            'type': 'type',
            'weather': 'weather',
            'terrain': 'terrain',
            'flora': 'flora',
            'fauna': 'fauna',
            'temperature': 'temperature',
            'humidity': 'humidity',
            'lighting': 'lighting',
            'visibility': 'visibility',
            'noise_ambient': 'noise_ambient',
            'noise_peak': 'noise_peak'
        }
        self._unstructured = unstructured
        self._type = type
        self._weather = weather
        self._terrain = terrain
        self._flora = flora
        self._fauna = fauna
        self._temperature = temperature
        self._humidity = humidity
        self._lighting = lighting
        self._visibility = visibility
        self._noise_ambient = noise_ambient
        self._noise_peak = noise_peak

    @classmethod
    def from_dict(cls, dikt) -> 'SimEnvironment':
        """Returns the dict as a model

        :param dikt: A dict.
        :type: dict
        :return: The SimEnvironment of this SimEnvironment.  # noqa: E501
        :rtype: SimEnvironment
        """
        return util.deserialize_model(dikt, cls)

    @property
    def unstructured(self) -> str:
        """Gets the unstructured of this SimEnvironment.

        Natural language, plain text description of the environment  # noqa: E501

        :return: The unstructured of this SimEnvironment.
        :rtype: str
        """
        return self._unstructured

    @unstructured.setter
    def unstructured(self, unstructured: str):
        """Sets the unstructured of this SimEnvironment.

        Natural language, plain text description of the environment  # noqa: E501

        :param unstructured: The unstructured of this SimEnvironment.
        :type unstructured: str
        """

        self._unstructured = unstructured

    @property
    def type(self) -> SimEnvironmentTypeEnum:
        """Gets the type of this SimEnvironment.


        :return: The type of this SimEnvironment.
        :rtype: SimEnvironmentTypeEnum
        """
        return self._type

    @type.setter
    def type(self, type: SimEnvironmentTypeEnum):
        """Sets the type of this SimEnvironment.


        :param type: The type of this SimEnvironment.
        :type type: SimEnvironmentTypeEnum
        """
        if type is None:
            raise ValueError("Invalid value for `type`, must not be `None`")  # noqa: E501

        self._type = type

    @property
    def weather(self) -> WeatherTypeEnum:
        """Gets the weather of this SimEnvironment.


        :return: The weather of this SimEnvironment.
        :rtype: WeatherTypeEnum
        """
        return self._weather

    @weather.setter
    def weather(self, weather: WeatherTypeEnum):
        """Sets the weather of this SimEnvironment.


        :param weather: The weather of this SimEnvironment.
        :type weather: WeatherTypeEnum
        """

        self._weather = weather

    @property
    def terrain(self) -> TerrainTypeEnum:
        """Gets the terrain of this SimEnvironment.


        :return: The terrain of this SimEnvironment.
        :rtype: TerrainTypeEnum
        """
        return self._terrain

    @terrain.setter
    def terrain(self, terrain: TerrainTypeEnum):
        """Sets the terrain of this SimEnvironment.


        :param terrain: The terrain of this SimEnvironment.
        :type terrain: TerrainTypeEnum
        """

        self._terrain = terrain

    @property
    def flora(self) -> FloraTypeEnum:
        """Gets the flora of this SimEnvironment.


        :return: The flora of this SimEnvironment.
        :rtype: FloraTypeEnum
        """
        return self._flora

    @flora.setter
    def flora(self, flora: FloraTypeEnum):
        """Sets the flora of this SimEnvironment.


        :param flora: The flora of this SimEnvironment.
        :type flora: FloraTypeEnum
        """

        self._flora = flora

    @property
    def fauna(self) -> FaunaTypeEnum:
        """Gets the fauna of this SimEnvironment.


        :return: The fauna of this SimEnvironment.
        :rtype: FaunaTypeEnum
        """
        return self._fauna

    @fauna.setter
    def fauna(self, fauna: FaunaTypeEnum):
        """Sets the fauna of this SimEnvironment.


        :param fauna: The fauna of this SimEnvironment.
        :type fauna: FaunaTypeEnum
        """

        self._fauna = fauna

    @property
    def temperature(self) -> float:
        """Gets the temperature of this SimEnvironment.

        numerical temperature in degrees Fahrenheit  # noqa: E501

        :return: The temperature of this SimEnvironment.
        :rtype: float
        """
        return self._temperature

    @temperature.setter
    def temperature(self, temperature: float):
        """Sets the temperature of this SimEnvironment.

        numerical temperature in degrees Fahrenheit  # noqa: E501

        :param temperature: The temperature of this SimEnvironment.
        :type temperature: float
        """

        self._temperature = temperature

    @property
    def humidity(self) -> float:
        """Gets the humidity of this SimEnvironment.

        Numerical relative humidity, in percentage  # noqa: E501

        :return: The humidity of this SimEnvironment.
        :rtype: float
        """
        return self._humidity

    @humidity.setter
    def humidity(self, humidity: float):
        """Sets the humidity of this SimEnvironment.

        Numerical relative humidity, in percentage  # noqa: E501

        :param humidity: The humidity of this SimEnvironment.
        :type humidity: float
        """

        self._humidity = humidity

    @property
    def lighting(self) -> LightingTypeEnum:
        """Gets the lighting of this SimEnvironment.


        :return: The lighting of this SimEnvironment.
        :rtype: LightingTypeEnum
        """
        return self._lighting

    @lighting.setter
    def lighting(self, lighting: LightingTypeEnum):
        """Sets the lighting of this SimEnvironment.


        :param lighting: The lighting of this SimEnvironment.
        :type lighting: LightingTypeEnum
        """

        self._lighting = lighting

    @property
    def visibility(self) -> VisibilityTypeEnum:
        """Gets the visibility of this SimEnvironment.


        :return: The visibility of this SimEnvironment.
        :rtype: VisibilityTypeEnum
        """
        return self._visibility

    @visibility.setter
    def visibility(self, visibility: VisibilityTypeEnum):
        """Sets the visibility of this SimEnvironment.


        :param visibility: The visibility of this SimEnvironment.
        :type visibility: VisibilityTypeEnum
        """

        self._visibility = visibility

    @property
    def noise_ambient(self) -> AmbientNoiseEnum:
        """Gets the noise_ambient of this SimEnvironment.


        :return: The noise_ambient of this SimEnvironment.
        :rtype: AmbientNoiseEnum
        """
        return self._noise_ambient

    @noise_ambient.setter
    def noise_ambient(self, noise_ambient: AmbientNoiseEnum):
        """Sets the noise_ambient of this SimEnvironment.


        :param noise_ambient: The noise_ambient of this SimEnvironment.
        :type noise_ambient: AmbientNoiseEnum
        """

        self._noise_ambient = noise_ambient

    @property
    def noise_peak(self) -> PeakNoiseEnum:
        """Gets the noise_peak of this SimEnvironment.


        :return: The noise_peak of this SimEnvironment.
        :rtype: PeakNoiseEnum
        """
        return self._noise_peak

    @noise_peak.setter
    def noise_peak(self, noise_peak: PeakNoiseEnum):
        """Sets the noise_peak of this SimEnvironment.


        :param noise_peak: The noise_peak of this SimEnvironment.
        :type noise_peak: PeakNoiseEnum
        """

        self._noise_peak = noise_peak
