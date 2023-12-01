import uuid
from dataclasses import dataclass
from typing import List
from abc import ABC, abstractmethod
from swagger_server.models import (
    Character,
    Scenario
)
from swagger_server.models.probe import Probe  # noqa: F401,E501
from .itm_character_simulator import CharacterSimulation


@dataclass
class ProbeObject:
    """Class to represent a probe object."""
    probe: Probe
    choice: str
    justification: str
    probe_number: int

class ITMProbeSystem(ABC):
    """Class to represent and manipulate the probe system."""

    def __init__(self):
        """
        Initialize an instance of ITMProbeSystem.
        """
        self.scenario: Scenario = None
        self.probe_count = 0
        self.probes = {}
    """
    commenting out to test using probeYaml in itm_probe_reader to do this
    def respond_to_probe(
            self,
            probe_id: str,
            choice: str,
            justification: str = None
        ) -> None:
        \"""
        Respond to a probe from the probe system.

        Args:
            probe_id: The ID of the probe.
            character_id: The ID of the character chosen to respond to the probe.
            explanation: An explanation for the response (optional).

        Returns:
            None.
        \"""
        probe: ProbeObject = self.probes[probe_id]
        probe.choice = choice
        probe.justification = justification
        # Possibly add assessed checks from probe answers
        # for p in self.scenario.state.characters:
        #     if p.id == choice:
        #         p.assessed = True
        #         break
        """

    def _get_probe_id(self):
        return "probe_" + str(uuid.uuid4())
    
    def _get_probe_option_id(self):
        return "probe_option_" + str(uuid.uuid4())
        
    def _find_this_character_simulation(self, character: Character, character_simulations: List[CharacterSimulation],):
        """
        Find the character simulation object for a specific character.

        Args:
            character (character): The character object to find its matching simulation.
            character_simulations (list): List of character simulation objects.

        Returns:
            CharacterSimulation or None: The simulation object for the specified character, or None if no simulation is found.
        """

        this_characters_simulation = None
        for character_simulation in character_simulations:
            if character_simulation.character.id == character.id:
                this_characters_simulation = character_simulation
                break
        return this_characters_simulation
