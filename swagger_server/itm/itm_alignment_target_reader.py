import yaml
from swagger_server.models import (
    AlignmentTarget,
    KDMAValue
)

class ITMAlignmentTargetReader:
    """Class for converting YAML data to ITM scenarios."""

    COUNTER: int = 1

    def init_from_yaml(self, yaml_path: str):
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

    def init_from_kdmas(self, af: float, mf: float, ps: float, ss: float):
        """
        Initialize the class with the specified KDMA values.

        Args:
            af: an Affiliation Focus KDMA value.
            mf: a Merit Focus KDMA value.
            ps: a Personal Safety KDMA value.
            ss: a Search vs. Stay KDMA value.
        """
        self.alignment_target = AlignmentTarget(
            id=f"target{ITMAlignmentTargetReader.COUNTER}",
            kdma_values=self._extract_kdma_values(af, mf, ps, ss)
        )
        ITMAlignmentTargetReader.COUNTER += 1

    def _extract_kdma_values(self, af: float, mf: float, ps: float, ss: float):
        kdma_values = []
        kdma_values.append(KDMAValue(kdma='affiliation', value=af))
        kdma_values.append(KDMAValue(kdma='merit', value=mf))
        kdma_values.append(KDMAValue(kdma='personal_safety', value=ps))
        kdma_values.append(KDMAValue(kdma='search', value=ss))
        return kdma_values

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
