# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.action import Action  # noqa: E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: E501
from swagger_server.models.scenario import Scenario  # noqa: E501
from swagger_server.models.state import State  # noqa: E501
from swagger_server.models.vitals import Vitals  # noqa: E501
from swagger_server.test import BaseTestCase


class TestItmTa2EvalController(BaseTestCase):
    """ItmTa2EvalController integration test stubs"""

    def test_apply_decompression_needle(self):
        """Test case for apply_decompression_needle

        Apply a decompression needle to a casualty
        """
        query_string = [('session_id', 'session_id_example'),
                        ('location', 'location_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/applyDecompressionNeedle'.format(casualty_id='casualty_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_apply_hemostatic_gauze(self):
        """Test case for apply_hemostatic_gauze

        Apply hemostatic gauze to a casualty
        """
        query_string = [('session_id', 'session_id_example'),
                        ('location', 'location_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/applyHemostaticGauze'.format(casualty_id='casualty_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_apply_nasal_trumpet(self):
        """Test case for apply_nasal_trumpet

        Apply a nasal trumpet to a casualty
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/applyNasalTrumpet'.format(casualty_id='casualty_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_apply_pressure_bandage(self):
        """Test case for apply_pressure_bandage

        Apply a pressure bandage to a casualty
        """
        query_string = [('session_id', 'session_id_example'),
                        ('location', 'location_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/applyPressureBandage'.format(casualty_id='casualty_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_apply_tourniquet(self):
        """Test case for apply_tourniquet

        Apply a tourniquet to a casualty
        """
        query_string = [('session_id', 'session_id_example'),
                        ('location', 'location_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/applyTourniquet'.format(casualty_id='casualty_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_apply_treatment(self):
        """Test case for apply_treatment

        Apply a treatment to a casualty
        """
        query_string = [('session_id', 'session_id_example'),
                        ('tool', 'tool_example'),
                        ('location', 'location_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/applyTreatment'.format(casualty_id='casualty_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_check_vital(self):
        """Test case for check_vital

        Assess and retrieve a vital sign
        """
        query_string = [('session_id', 'session_id_example'),
                        ('vital_sign', 'vital_sign_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/checkVital'.format(casualty_id='casualty_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_check_vitals(self):
        """Test case for check_vitals

        Assess and retrieve all casualty vital signs
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/checkVitals'.format(casualty_id='casualty_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_direct_to_safezone(self):
        """Test case for direct_to_safezone

        Direct casualties to the safe zone
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/{scenario_id}/directToSafezone'.format(scenario_id='scenario_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_alignment_target(self):
        """Test case for get_alignment_target

        Retrieve alignment target for the scenario
        """
        query_string = [('session_id', 'session_id_example'),
                        ('scenario_id', 'scenario_id_example')]
        response = self.client.open(
            '/ta2/getAlignmentTarget',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_available_actions(self):
        """Test case for get_available_actions

        Get a list of currently available ADM actions
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/{scenario_id}/getAvailableActions'.format(scenario_id='scenario_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_available_actions2(self):
        """Test case for get_available_actions2

        Get a list of currently available ADM action types
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/{scenario_id}/getAvailableActionTypes'.format(scenario_id='scenario_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_consciousness(self):
        """Test case for get_consciousness

        Check casualty consciousness
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/checkConsciousness'.format(casualty_id='casualty_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_heart_rate(self):
        """Test case for get_heart_rate

        Check casualty heart rate
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/checkHeartRate'.format(casualty_id='casualty_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_respiratory_rate(self):
        """Test case for get_respiratory_rate

        Check casualty respiratory rate
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/checkRespiratoryRate'.format(casualty_id='casualty_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_get_scenario_state(self):
        """Test case for get_scenario_state

        Retrieve scenario state
        """
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/{scenario_id}/getState'.format(scenario_id='scenario_id_example'),
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_start_scenario(self):
        """Test case for start_scenario

        Get the next scenario
        """
        query_string = [('session_id', 'session_id_example'),
                        ('scenario_id', 'scenario_id_example')]
        response = self.client.open(
            '/ta2/scenario',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_start_session(self):
        """Test case for start_session

        Start a new session
        """
        query_string = [('adm_name', 'adm_name_example'),
                        ('session_type', 'session_type_example'),
                        ('max_scenarios', 56)]
        response = self.client.open(
            '/ta2/startSession',
            method='GET',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_tag_casualty(self):
        """Test case for tag_casualty

        Tag a casualty with a triage category
        """
        query_string = [('session_id', 'session_id_example'),
                        ('tag', 'tag_example')]
        response = self.client.open(
            '/ta2/casualty/{casualty_id}/tag'.format(casualty_id='casualty_id_example'),
            method='POST',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))

    def test_take_action(self):
        """Test case for take_action

        Take an action within a scenario
        """
        body = Action()
        query_string = [('session_id', 'session_id_example')]
        response = self.client.open(
            '/ta2/takeAction',
            method='POST',
            data=json.dumps(body),
            content_type='application/json',
            query_string=query_string)
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    import unittest
    unittest.main()
