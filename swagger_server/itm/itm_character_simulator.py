import copy
import random
from dataclasses import dataclass
from typing import List, Union
from swagger_server.models.character import Character
from swagger_server.models.scenario import Scenario
from swagger_server.models.vitals import Vitals


@dataclass
class CharacterSimulation:
    """Class to represent a character simulation over time."""
    character: Character
    # correct_tag: str
    # start_vitals: Vitals
    # current_vitals: Vitals
    # treatments_applied: str
    # treatments_needed: List[str]
    # stable: bool
    # deceased: bool

    # Changes over time, leaving out for now
    # A value less than 0 (e.g. -1) ensures the character does not die
    # deceased_after_minutes: float
    # hrpmin_index: int = 0
    # hrpmin_change: Union[int, List[int]] = 0
    # mmhg_index: int = 0
    # mmhg_change: Union[int, List[int]] = 0
    # rr_index: int = 0
    # rr_change: Union[int, List[int]] = 0
    # spo2_index: int = 0
    # spo2_change: Union[int, List[int]] = 0



class ITMCharacterSimulator:
    """Class to represent and manipulate a character during the simulation."""

    def __init__(self):
        """
        Initialize an instance of ITMCharacterSimulator.
        """
        self.scenario: Scenario
        self.character_simulations: List[CharacterSimulation]

    def get_change(self, vital_value, index_attr, character):
        """
        Get the change value for a vital based on the index attribute.

        Args:
            vital_value: The value of the vital (can be int or list of int).
            index_attr: The index attribute corresponding to the vital.
            character: The character simulation object.

        Returns:
            The change value for the vital.
        """
        # if isinstance(vital_value, list):
        #     index = getattr(character, index_attr)
        #     if index < len(vital_value):
        #         change = vital_value[index]
        #         if index + 1 == len(vital_value):
        #             return change
        #         setattr(character, index_attr, index + 1)
        #         return change
        # return vital_value
        pass

    def get_vital_changes(self, character: CharacterSimulation):
        """
        Get the changes in vital signs for a character simulation.

        Args:
            character: The character simulation object.

        Returns:
            A tuple containing the changes in vital signs.
        """
        # hrpmin_change = self.get_change(
        #     character.hrpmin_change, 'hrpmin_index', character)
        # mmhg_change = self.get_change(
        #     character.mmhg_change, 'mmhg_index', character)
        # rr_change = self.get_change(
        #     character.rr_change, 'rr_index', character)
        # spo2_change = self.get_change(
        #     character.spo2_change, 'spo2_index', character)
        # conscious = True # TBD
        # responsive = True # TBD
        # breathing = True # TBD
        # return (conscious, responsive, breathing, hrpmin_change, mmhg_change, rr_change, spo2_change)
        pass

    def update_vitals(self, time_elapsed_scenario_time: float) -> None:
        """
        Update the vitals of character simulations based on elapsed time.

        Args:
            time_elapsed_scenario_time: The elapsed time in the scenario.

        Returns:
            None.
        """
        # for character in self.character_simulations:
        #    if character.stable or character.deceased:
        #        continue
        #
        #    if character.deceased_after_minutes > 0:
        #        if time_elapsed_scenario_time >= character.deceased_after_minutes:
        #            character.deceased = True
        #            self.terminate_character(character)
        #            continue
        #
        #    vital_changes = self.get_vital_changes(character)
        #    character.current_vitals.conscious += vital_changes[0]
        #    character.current_vitals.responsive += vital_changes[1]
        #    character.current_vitals.breathing += vital_changes[2]
        #    character.current_vitals.hrpmin += vital_changes[3]
        #    character.current_vitals.mm_hg += vital_changes[4]
        #    character.current_vitals.rr += vital_changes[5]
        #    character.current_vitals.sp_o2 += vital_changes[6]
        #    character.character.vitals = copy.deepcopy(character.current_vitals)
        pass

    def terminate_character(self, character: CharacterSimulation):
        """
        Terminate a character by making all of their vital signs
        set to zero.

        Args:
            character: The character simulation object to terminate.

        Returns:
            None.
        """
        character.current_vitals.conscious = False
        character.current_vitals.responsive = False
        character.current_vitals.breathing = "NONE"
        character.current_vitals.hrpmin = 0
        #character.current_vitals.mm_hg = 0
        #character.current_vitals.rr = 0
        #character.current_vitals.sp_o2 = 0
        character.character.vitals = copy.deepcopy(character.current_vitals)

    def treat_character(self, character_id: str, supply: str) -> float:
        """
        Treat a character with a medical supply.

        Args:
            character_id: The ID of the character.
            supply: The name of the supply.

        Returns:
            The time elapsed during the treatment as a float.
        """
        time_elapsed = round(random.uniform(0.1, 5.0), 2)
        # for character in self.character_simulations:
        #     if character.character.id == character_id:
        #         character.stable = True
        #         character.treatments_applied.append(supply)
        #         # TODO make treatement time be based off of medical supplies
        #         # for supply in self.scenario.medical_supplies:
        #         #     if supply.name == medical_supply:
        #         #         supply.quantity -= 1
        #         # time_elapsed = medical_supply_details[medical_supply].time_to_apply
        #         return time_elapsed
        return time_elapsed


    def check_on_setup_if_characters_are_deceased(self) -> None:
        """
        Checks if a character is deceased on a scenario's start. If the character
        is deceased then the character's vitals is terminated and their vitals
        are all set to zero.

        Returns:
            None.
        """
        pass
        # for character in self.character_simulations:
        #     if character.deceased:
        #         self.terminate_character(character)
        #         continue

    def setup_characters(self, scenario: Scenario,
                       character_simulations: List[CharacterSimulation]) -> None:
        """
        Set up characters in the character simulator.

        Args:
            scenario: The scenario object containing the characters.
            character_simulations: A list of character simulation objects.

        Returns:
            None.
        """
        self.scenario = scenario
        self.character_simulations = character_simulations
        self.check_on_setup_if_characters_are_deceased()
