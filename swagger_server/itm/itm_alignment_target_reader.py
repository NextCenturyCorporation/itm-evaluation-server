import yaml
from swagger_server.models import (
    AlignmentTarget,
    KDMAValue,
    KDMAValueParametersInner
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


    def init_from_kdmas_new(self, pid: str, name: str, acronym: str, parameters: dict[str, float]):
        """
        Initialize the class with the specified KDMA data.

        Args:
            pid: the pid of the user with these kdmas
            name: the TA1 name of the kdma
            kdma_acronynm: the two-letter acronym of the kdma
            parameters: a dictionary of kdma parameters
        """
        kdma_values = []
        kdma_parameters = []
        for param_name, param_value in parameters.items():
            kdma_parameters = KDMAValueParametersInner(name=param_name, value=param_value)

        kdma_values.append(KDMAValue(kdma=name, type='single', parameters=kdma_parameters))

        self.alignment_target = AlignmentTarget(
            id=f"target{pid}_{acronym}",
            kdma_values=kdma_values
        )


    def init_from_kdmas(self, mj: float, io: float):
        """
        Initialize the class with the specified KDMA values.

        Args:
            mj: a Moral judgement KDMA value.
            io: an Ingroup Bias KDMA value.
        """
        self.alignment_target = AlignmentTarget(
            id=f"target{ITMAlignmentTargetReader.COUNTER}",
            kdma_values=self._extract_kdma_values(mj, io)
        )
        ITMAlignmentTargetReader.COUNTER += 1

    def _extract_kdma_values(self, mj: float, io: float):
        kdma_values = []
        kdma_values.append(KDMAValue(kdma='Moral judgement', value=mj))
        kdma_values.append(KDMAValue(kdma='Ingroup Bias', value=io))
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
