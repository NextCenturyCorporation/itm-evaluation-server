import builtins
import logging
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    State
)
from swagger_server.itm import ITMScenario
from swagger_server.config_util import Configuration


class P2triageScenario(ITMScenario):

    def __init__(self, yaml_path, session, ta1_name, training = False) -> None:
        super().__init__(yaml_path, session, ta1_name, training)

        # Tells the server to get its probe data from characters
        config = Configuration.get_config()
        self.inferred_responses = config[builtins.config_group].getboolean("INFERRED_RESPONSES", fallback=False)
        self.probe_map: dict[str, dict[str, str]] = None
        self.treatment_order: list = None
        self.character_map: dict = None
        if self.inferred_responses:
            self.training = False
            self.probe_map = {}
            self.treatment_order = []


    @staticmethod
    def clear_hidden_data(state: State, training: bool):
        if not training:
            for character in state.characters:
                character.medical_condition = None
                character.attribute_rating = None

        for character in state.characters:
            character.unstructured_posttreatment = None


    # Maintain map from generic (e.g., "Patient N") to real character name (e.g., "Military 3")
    def init_character_map(self)-> dict:
        self.character_map = {}
        first_scene_id = self.first_scene
        first_scene = None
        for scene in self.isd.scenes:
            if scene.id == first_scene_id:
                first_scene = scene
                break
        if not first_scene:
            logging.error("Could not determine first scene in inferred response scenario.")

        # First real scene contains the patients with the real name after semicolon in unstructured_posttreatment
        for character in first_scene.state.characters:
            self.character_map[character.id] = (character.unstructured_posttreatment.split(';')[-1]).strip()


    # Generates probes for Open World scenarios from Scene data
    # Adapted from itm-ingest/feb2026_probe_matcher.py
    def generate_probe_mapping(self):
        # Build probe map from scenario data
        for scene in self.isd.scenes:
            if not scene.id.startswith('Scene'):
                continue # Only parse the original binary choice scenes
            patient_name_map = {}
            response_map = {}
            scene.state.characters
            for character in scene.state.characters:
                # Sim patient name is after semicolon in 'unstructured'
                unstructured = character.unstructured
                sim_patient_name = unstructured.split(";")[-1].strip()
                patient_name_map[character.id] = sim_patient_name
            for mapping in scene.action_mappings:
                probe_id = mapping.probe_id
                choice_id = mapping.choice
                character_id = mapping.character_id
                if probe_id and choice_id and character_id in patient_name_map:
                    response_map[patient_name_map[character_id]] = choice_id
                    self.probe_map[probe_id] = response_map


    def generate_scenario_data(self):
        super().generate_scenario_data()
        if self.inferred_responses:
            self.generate_probe_mapping()
            self.init_character_map()


    def first_engaged(self, characters: list)-> str:
        for character in self.treatment_order:
            real_name = self.character_map.get(character)
            if real_name in characters:
                return real_name
        return None


    def send_probes(self):
        logging.debug(f"Patient treatment order: {self.treatment_order}.")
        for probe_id, response_map in self.probe_map.items():
            first_char = self.first_engaged(list(response_map.keys()))
            if first_char:
                self.respond_to_probe("N/A", probe_id, response_map[first_char], "N/A")


    def action_taken(self, action: Action):
        if self.inferred_responses and action.action_type == ActionTypeEnum.TREAT_PATIENT:
            if action.character_id not in self.treatment_order:
                self.treatment_order.append(action.character_id)


    def end_scenario(self):
        if self.inferred_responses:
            self.send_probes()
        self.session.end_scenario()
