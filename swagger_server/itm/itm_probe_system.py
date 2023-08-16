import uuid
from dataclasses import dataclass
from typing import List
from abc import ABC, abstractmethod
from swagger_server.models import (
    Casualty,
    Scenario
)
from swagger_server.models.probe import Probe  # noqa: F401,E501
from .itm_casualty_simulator import CasualtySimulation


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

    def respond_to_probe(
            self,
            probe_id: str,
            choice: str,
            justification: str = None
        ) -> None:
        """
        Respond to a probe from the probe system.

        Args:
            probe_id: The ID of the probe.
            casualty_id: The ID of the casualty chosen to respond to the probe.
            explanation: An explanation for the response (optional).

        Returns:
            None.
        """
        probe: ProbeObject = self.probes[probe_id]
        probe.choice = choice
        probe.justification = justification
        # Possibly add assessed checks from probe answers
        # for p in self.scenario.state.casualties:
        #     if p.id == choice:
        #         p.assessed = True
        #         break

    def _get_probe_id(self):
        return "probe_" + str(uuid.uuid4())
    
    def _get_probe_option_id(self):
        return "probe_option_" + str(uuid.uuid4())
        
    def _find_this_casualty_simulation(self, casualty: Casualty, casualty_simulations: List[CasualtySimulation],):
        """
        Find the casualty simulation object for a specific casualty.

        Args:
            casualty (casualty): The casualty object to find its matching simulation.
            casualty_simulations (list): List of casualty simulation objects.

        Returns:
            CasualtySimulation or None: The simulation object for the specified casualty, or None if no simulation is found.
        """

        this_casualties_simulation = None
        for casualty_simulation in casualty_simulations:
            if casualty_simulation.casualty.id == casualty.id:
                this_casualties_simulation = casualty_simulation
                break
        return this_casualties_simulation
