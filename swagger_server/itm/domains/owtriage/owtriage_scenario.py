import logging
from swagger_server.models import (
    Action,
    ActionTypeEnum,
    State,
    Vitals
)
from swagger_server.itm import ITMScenario


class OWTriageScenario(ITMScenario):

    UNSEEN_TEXT = "This patient is not currently visible; you would have to move this patient's location."

    def __init__(self, yaml_path, session, ta1_name, training = False) -> None:
        super().__init__(yaml_path, session, ta1_name, training)

        self.probe_map: dict[str, dict[str, str]] = None
        self.treatment_order: list = None
        self.training = False
        self.probe_map = {}
        self.treatment_order = []
        self.last_action = None
        self.last_character = None


    def clear_hidden_data(self, state: State, training: bool):
        if not training:
            for character in state.characters:
                character.medical_condition = None
                character.attribute_rating = None

        for character in state.characters:
            character.unstructured_near = None
            character.unstructured_far = None
            character.unstructured_treated_far = None
            character.unstructured_treated_near = None
            character.distance = None
            character.treated = None
            if not character.nearby:
                character.tag = None
            if not (self.last_action == ActionTypeEnum.CHECK_VITALS and character.id == self.last_character):
                character.vitals = Vitals() # Hide vitals unless just checked on this character
            if character.unseen:
                character.unstructured = self.UNSEEN_TEXT


    # Generates probes for Open World scenarios from Scene data
    # Adapted from itm-ingest/feb2026_probe_matcher.py, but then altered further since we now use Patient N for character ids
    def generate_probe_mapping(self):
        # Build probe map from scenario data
        for scene in self.isd.scenes:
            if not scene.id.startswith('Scene'):
                continue # Only parse the original binary choice scenes
            response_map = {}
            character_ids = [character.id for character in scene.state.characters]
            for mapping in scene.action_mappings:
                probe_id = mapping.probe_id
                if 'Fake' in probe_id:
                    continue # Skip fake probes that are only there to document patients who aren't in any probes
                choice_id = mapping.choice
                character_id = mapping.character_id
                if probe_id and choice_id and character_id in character_ids:
                    response_map[character_id] = choice_id
                    self.probe_map[probe_id] = response_map


    def generate_scenario_data(self):
        super().generate_scenario_data()
        self.generate_probe_mapping()


    def first_engaged(self, characters: list)-> str:
        for character in self.treatment_order:
            if character in characters:
                return character
        return None


    def send_probes(self):
        logging.info(f"{self.session.log_id}: Patient treatment order: {self.treatment_order}.")
        for probe_id, response_map in self.probe_map.items():
            first_char = self.first_engaged(list(response_map.keys()))
            if first_char:
                self.respond_to_probe("N/A", probe_id, response_map[first_char], "N/A")


    def action_taken(self, action: Action):
        self.last_action = action.action_type
        self.last_character = action.character_id
        self.clear_hidden_data(self.session.state, self.session.kdma_training)
        if action.action_type == ActionTypeEnum.TREAT_PATIENT:
            if action.character_id not in self.treatment_order:
                self.treatment_order.append(action.character_id)


    def change_scene(self, next_scene_id):
        super().change_scene(next_scene_id)
        self.session.state.elapsed_time = 0 # Needed to support evac scene in OW3


    def end_scenario(self):
        self.send_probes()
        self.session.end_scenario()
