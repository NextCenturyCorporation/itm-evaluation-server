import yaml
from swagger_server.models import (
    AlignmentTarget,
    KDMAValue
)

class ITMAlignmentTargetReader:
    """Class for converting YAML data to ITM scenarios."""

    def __init__(self, yaml_path: str):
        """
        Initialize the class with YAML data from a file path.

        Args:
            yaml_path: The file path to the YAML data.
        """
        with open(yaml_path, 'r') as file:
            self.yaml_data = yaml.safe_load(file)
            self.alignment_target = AlignmentTarget(
                id=self.yaml_data['id'],
                kdma_values=self._extract_alignment_targets()
            )
        file.close()

    def _extract_alignment_targets(self):
        alignment_targets = []
        for item in self.yaml_data.get('kdma_values', []):
            kdma = item.get('kdma')
            value = item.get('value')
            kmda_value = KDMAValue(
                kdma=kdma,
                value=value if isinstance(value, (float, int)) else (1 if value == "+" else -1)
            )
            alignment_targets.append(kmda_value)
        return alignment_targets
