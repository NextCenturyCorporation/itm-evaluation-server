import glob
import os
import yaml
from typing import List, Dict
from dataclasses import dataclass, field
from swagger_server.models.probe import Probe  # noqa: F401,E501
from swagger_server.models.probe_option import ProbeOption  # noqa: F401,E501
from swagger_server.models.action import Action
from .itm_probe_system import ITMProbeSystem


@dataclass 
class ProbeYamlOptions:
    id: str = None
    value: str = None
    ta1_id: str = None
    assoc_action: Action = None

    @staticmethod
    def from_dict(obj: Dict):
        return ProbeYamlOptions(
            id=obj.get("id"),
            value=obj.get("value"),
            ta1_id=obj.get("ta1_id"),
            assoc_action=obj.get("assoc_action")
        )
    
    def to_probe_option(self):
        return ProbeOption(
            id=self.ta1_id,
            value=self.value
        )


@dataclass
class ProbeYaml:
    id: str = None
    scenario_id: str = None
    type: str = None
    prompt: str = None
    state: Dict = None
    choice: str = None
    justification: str = None
    options: List[ProbeYamlOptions] = field(default_factory=list)

    @staticmethod
    def from_dict(obj: Dict):
        return ProbeYaml(
            id=obj.get("id"),
            scenario_id=obj.get("scenario_id"),
            type=obj.get("type"),
            prompt=obj.get("prompt"),
            state=obj.get("state"),
            options=[ProbeYamlOptions.from_dict(option) for option in obj.get("options", [])]
        )
    
    def to_probe(self, state):
        options = [option.to_probe_option() for option in self.options]
        return Probe(
            id=self.id,
            scenario_id=self.scenario_id,
            type=self.type,
            prompt=self.prompt,
            state=state,
            options=options
        )


class ITMProbeReader(ITMProbeSystem):
    """Class to represent and manipulate the probe system."""

    def __init__(self, yaml_path):
        """
        Initialize an instance of ITMProbeReader.
        """
        super().__init__()
        self.yaml_path = yaml_path
        self.probe_yamls: List[ProbeYaml] = self.read_all_probes_yamls_for_scenario()
        self.current_probe_index = 0
        self.probe_count = len(self.probe_yamls)

    def read_all_probes_yamls_for_scenario(self) -> List[ProbeYaml]:
        """
        Reads all probe YAML files from the provided 'yaml_path' directory and 
        its subdirectory named after 'scenario_name', and stores them in a list.
        """
        # normalize slashes in path according to operating system (linux vs windows)
        self.yaml_path = os.path.normpath(self.yaml_path)
        
        probe_yamls = []
        probe_files = sorted(glob.glob(os.path.join(self.yaml_path, 'probe*.yaml')))
        for filepath in probe_files:
            with open(filepath, 'r') as file:
                yaml_text = file.read()
                probe_yaml = self.read_probe_from_yaml(yaml_text)
                probe_yamls.append(probe_yaml)
        return probe_yamls

    def read_probe_from_yaml(self, yaml_text: str):
        probe_dict = yaml.safe_load(yaml_text)
        probe_yaml = ProbeYaml.from_dict(probe_dict)
        return probe_yaml
    
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
            choice: The ID of the option to respond to the probe.
            justification: An explanation for the response (optional).

        Returns:
            None.
        """
        probe = next((probe for probe in self.probe_yamls if probe.id == probe_id), None)
        if probe:
            probe.choice = choice
            probe.justification = justification
        # Possibly add assessed checks from probe answers
        # for p in self.scenario.state.characters:
        #     if p.id == choice:
        #         p.assessed = True
        #         break
