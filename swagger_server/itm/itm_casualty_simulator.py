import copy
import random
from dataclasses import dataclass
from typing import List, Union
from swagger_server.models.casualty import Casualty
from swagger_server.models.scenario import Scenario
from swagger_server.models.vitals import Vitals


@dataclass
class CasualtySimulation:
    """Class to represent a casualty simulation over time."""
    casualty: Casualty
    # correct_tag: str
    # start_vitals: Vitals
    # current_vitals: Vitals
    # treatments_applied: str
    # treatments_needed: List[str]
    # stable: bool
    # deceased: bool

    # Changes over time, leaving out for now
    # A value less than 0 (ex. -1) ensures the casualty does not die
    # deceased_after_minutes: float
    # hrpmin_index: int = 0
    # hrpmin_change: Union[int, List[int]] = 0
    # mmhg_index: int = 0
    # mmhg_change: Union[int, List[int]] = 0
    # rr_index: int = 0
    # rr_change: Union[int, List[int]] = 0
    # spo2_index: int = 0
    # spo2_change: Union[int, List[int]] = 0



class ITMCasualtySimulator:
    """Class to represent and manipulate a casualty during the simulation."""

    def __init__(self):
        """
        Initialize an instance of ITMCasualtySimulator.
        """
        self.scenario: Scenario
        self.casualty_simulations: List[CasualtySimulation]

    def get_change(self, vital_value, index_attr, casualty):
        """
        Get the change value for a vital based on the index attribute.

        Args:
            vital_value: The value of the vital (can be int or list of int).
            index_attr: The index attribute corresponding to the vital.
            casualty: The casualty simulation object.

        Returns:
            The change value for the vital.
        """
        # if isinstance(vital_value, list):
        #     index = getattr(casualty, index_attr)
        #     if index < len(vital_value):
        #         change = vital_value[index]
        #         if index + 1 == len(vital_value):
        #             return change
        #         setattr(casualty, index_attr, index + 1)
        #         return change
        # return vital_value
        pass

    def get_vital_changes(self, casualty: CasualtySimulation):
        """
        Get the changes in vital signs for a casualty simulation.

        Args:
            casualty: The casualty simulation object.

        Returns:
            A tuple containing the changes in vital signs.
        """
        # hrpmin_change = self.get_change(
        #     casualty.hrpmin_change, 'hrpmin_index', casualty)
        # mmhg_change = self.get_change(
        #     casualty.mmhg_change, 'mmhg_index', casualty)
        # rr_change = self.get_change(
        #     casualty.rr_change, 'rr_index', casualty)
        # spo2_change = self.get_change(
        #     casualty.spo2_change, 'spo2_index', casualty)
        # consciousness = True # TBD
        # return (consciousness, hrpmin_change, mmhg_change, rr_change, spo2_change)
        pass

    def update_vitals(self, time_elapsed_scenario_time: float) -> None:
        """
        Update the vitals of casualty simulations based on elapsed time.

        Args:
            time_elapsed_scenario_time: The elapsed time in the scenario.

        Returns:
            None.
        """
        # for casualty in self.casualty_simulations:
        #    if casualty.stable or casualty.deceased:
        #        continue
        #
        #    if casualty.deceased_after_minutes > 0:
        #        if time_elapsed_scenario_time >= casualty.deceased_after_minutes:
        #            casualty.deceased = True
        #            self.terminate_casualty(casualty)
        #            continue
        #
        #    vital_changes = self.get_vital_changes(casualty)
        #    casualty.current_vitals.consciousness += vital_changes[0]
        #    casualty.current_vitals.hrpmin += vital_changes[1]
        #    casualty.current_vitals.mm_hg += vital_changes[2]
        #    casualty.current_vitals.rr += vital_changes[3]
        #    casualty.current_vitals.sp_o2 += vital_changes[4]
        #    casualty.casualty.vitals = copy.deepcopy(casualty.current_vitals)
        pass

    def terminate_casualty(self, casualty: CasualtySimulation):
        """
        Terminate a casualty by making all of their vital signs
        set to zero.

        Args:
            casualty: The casualty simulation object to terminate.

        Returns:
            None.
        """
        casualty.current_vitals.consciousness = False
        casualty.current_vitals.hrpmin = 0
        casualty.current_vitals.mm_hg = 0
        casualty.current_vitals.rr = 0
        casualty.current_vitals.sp_o2 = 0
        casualty.casualty.vitals = copy.deepcopy(casualty.current_vitals)

    def treat_casualty(self, casualty_id: str, supply: str) -> float:
        """
        Treat a casualty with a medical supply.

        Args:
            casualty_id: The ID of the casualty.
            supply: The name of the supply.

        Returns:
            The time elapsed during the treatment as a float.
        """
        time_elapsed = round(random.uniform(0.1, 5.0), 2)
        # for casualty in self.casualty_simulations:
        #     if casualty.casualty.id == casualty_id:
        #         casualty.stable = True
        #         casualty.treatments_applied.append(supply)
        #         # TODO make treatement time be based off of medical supplies
        #         # for supply in self.scenario.medical_supplies:
        #         #     if supply.name == medical_supply:
        #         #         supply.quantity -= 1
        #         # time_elapsed = medical_supply_details[medical_supply].time_to_apply
        #         return time_elapsed
        return time_elapsed
        

    def check_on_setup_if_casualties_are_deceased(self) -> None:
        """
        Checks if a casualty is deceased on a scenario's start. If the casualty
        is deceased then the casualty's vitals is terminated and their vitals 
        are all set to zero.

        Returns:
            None.
        """
        pass
        # for casualty in self.casualty_simulations:
        #     if casualty.deceased:
        #         self.terminate_casualty(casualty)
        #         continue

    def setup_casualties(self, scenario: Scenario,
                       casualty_simulations: List[CasualtySimulation]) -> None:
        """
        Set up casualtys in the casualty simulator.

        Args:
            scenario: The scenario object containing the casualtys.
            casualty_simulations: A list of casualty simulation objects.

        Returns:
            None.
        """
        self.scenario = scenario
        self.casualty_simulations = casualty_simulations
        self.check_on_setup_if_casualties_are_deceased()
