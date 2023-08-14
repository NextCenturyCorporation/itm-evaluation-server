# coding: utf-8

from __future__ import absolute_import

from flask import json
from six import BytesIO

from swagger_server.models.action import Action  # noqa: E501
from swagger_server.models.alignment_target import AlignmentTarget  # noqa: E501
from swagger_server.models.scenario import Scenario  # noqa: E501
from swagger_server.models.state import State  # noqa: E501
from swagger_server.test import BaseTestCase


class TestItmTa2EvalController(BaseTestCase):
    """ItmTa2EvalController integration test stubs"""

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
