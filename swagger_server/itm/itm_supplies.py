from dataclasses import dataclass
from typing import List, Dict
from swagger_server.models.supplies import Supplies


@dataclass
class SupplyDetails:
    """Class to represent Supply details"""
    supply: Supplies = None
    time_to_apply: float = 0


class ITMSupplies:
    """
    Class for managing supplies in the ITM system.
    """

    def __init__(self):
        """
        Initialize an instance of ITMSupplies.
        """
        self.supplies_details: Dict[str, SupplyDetails] = {}

    def get_supplies(self):
        return self.supplies_details

    def setup_supply(self, supplies: List[Supplies], time_to_apply: float) -> None:
        """
        Set up supplies with their corresponding details.

        Args:
            supplies: A list of Supplies objects representing the available supplies.
            time_to_apply: The time taken to apply each supply in minutes.

        Returns:
            None
        """
        for supply in supplies:
            supply_details = SupplyDetails(
                supply=supply,
                time_to_apply=time_to_apply
            )
            self.supplies_details[supply.name] = supply_details
