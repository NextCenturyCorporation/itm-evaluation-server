import logging
from typing import List
from dataclasses import dataclass
from copy import deepcopy
from swagger_server.models import (
    Action, AlignmentTarget, InjuryStatusEnum, ProbeResponse, State, Vitals
)
from .itm_scenario_reader import ITMScenarioReader
from .itm_scene import ITMScene
from .itm_ta1_controller import ITMTa1Controller

@dataclass
class ITMScenarioData:
    scenes: List[ITMScene] = None
    current_scene :ITMScene = None

class ITMScenario:

    def __init__(self, yaml_path, session, training = False) -> None:
        self.yaml_path = yaml_path
        self.scene_type = 'adept' if 'adept' in self.yaml_path else 'soartech'
        self.training = training
        self.alignment_target: AlignmentTarget = None
        self.ta1_controller: ITMTa1Controller = None
        self.probes_sent = []
        self.probe_responses_sent = []
        from.itm_session import ITMSession
        self.session :ITMSession = session
        self.isd :ITMScenarioData
        self.id=''
        self.name=''

    # Hide vitals (if not already visited) and hidden injuries
    @staticmethod
    def clear_hidden_data(state :State):
        initially_visible_injuries = [InjuryStatusEnum.VISIBLE, InjuryStatusEnum.TREATED, InjuryStatusEnum.DISCOVERED]
        for character in state.characters:
            character.injuries[:] = \
                [injury for injury in character.injuries if injury.status in initially_visible_injuries]
            if not character.visited:
                character.unstructured_postassess = None
                character.vitals = Vitals()


    def generate_scenario_data(self):
        # isd is short for ITM Scenario Data
        isd = ITMScenarioData()

        scenario_reader = ITMScenarioReader(self.yaml_path)
        (scenario, isd.scenes) = \
            scenario_reader.read_scenario_from_yaml()
        isd.current_scene = [scene for scene in isd.scenes if scene.id == scenario.first_scene][0]
        logging.debug("First scene of scenario '%s' is '%s'.", scenario.id, isd.current_scene.id)
        for scene in isd.scenes:
            scene.training = self.training
            scene.parent_scenario = self
        self.isd = isd
        self.id = scenario.id
        self.name = scenario.name

    def set_controller(self, controller :ITMTa1Controller):
        self.ta1_controller = controller
        self.alignment_target = controller.alignment_target

    def get_available_actions(self) -> List[Action]:
        current_character_ids = {character.id for character in self.isd.current_scene.state.characters}
        actions = self.isd.current_scene.get_available_actions(self.session.state.supplies)

        # safe guarding that an action with character id of a removed character doesn't slip through the cracks
        filtered_actions = []
        filtered_out_actions = []

        for action in actions:
            if not getattr(action, 'character_id', None) or action.character_id in current_character_ids:
                filtered_actions.append(action)
            else:
                filtered_out_actions.append(action)
        
        # if actions are filtered out, that means there is a configuration issue in yaml file of available action to character not in scene
        if filtered_out_actions:
            logging.warning("Scene configuration issue: ignoring actions with an invalid character: %s", filtered_out_actions)

        return filtered_actions


    def respond_to_probe(self, probe_id, choice_id, justification):
        """
        Respond to the specified probe with the specified choice and justification

        Args:
            probe_id: The TA1 id of the probe
            choice_id: The TA1 id of the choice the ADM made
            justification: the choice justification provided by the ADM, if any
        """
        response = ProbeResponse(scenario_id=self.id, probe_id=probe_id, choice=choice_id,
                                 justification = '' if justification is None else justification)
        self.session.history.add_history(
            "Respond to TA1 Probe",
            {"session_id": self.session.session_id, "scenario_id": response.scenario_id, "probe_id": response.probe_id,
             "choice": response.choice, "justification": response.justification},
             None
            )
        if self.ta1_controller:
            try:
                self.ta1_controller.post_probe(probe_response=response)
                # Get and log probe response alignment if not training.
                if not self.session.kdma_training:
                    probe_response_alignment = \
                        self.ta1_controller.get_probe_response_alignment(
                        response.scenario_id,
                        response.probe_id
                    )
                    self.session.history.add_history(
                        "TA1 Probe Response Alignment",
                        {"session_id": self.ta1_controller.session_id,
                        "scenario_id": response.scenario_id,
                        "target_id": self.ta1_controller.alignment_target_id,
                        "probe_id": response.probe_id},
                        probe_response_alignment
                    )
                    alignment_scenario_id = probe_response_alignment['alignment_source'][0]['scenario_id']
                    if self.id != alignment_scenario_id:
                        logging.warning("\033[92mContamination in probe alignment! scenario is %s but alignment source scenario is %s.\033[00m", self.id, alignment_scenario_id)
            except:
                logging.exception("Exception posting probe response to TA1.")
        self.probes_sent.append(probe_id)
        self.probe_responses_sent.append(choice_id)
        logging.info("Responding to probe %s from scenario %s with choice %s.",
                     response.probe_id, response.scenario_id, response.choice)


    def change_scene(self, next_scene_id):
        if next_scene_id == ITMScene.END_SCENARIO_SENTINEL:
            self.isd.current_scene.state = None # Supports single-scenario sessions
            self.session.end_scenario()
            return

        next_scene = [scene for scene in self.isd.scenes if scene.id == next_scene_id]
        if next_scene == []:
            if isinstance(self.isd.current_scene.id, int) and isinstance(next_scene_id, int) \
                and self.isd.current_scene.id == next_scene_id - 1:
                pass # This is expected when scenario ids are simple indices
            else:
                logging.error("Scene configuration issue: next scene '%s' not found; ending scenario.", next_scene_id)
            self.isd.current_scene.state = None # Supports single-scenario sessions
            self.session.end_scenario()
            return

        previous_scene_characters = self.isd.current_scene.state.characters
        self.isd.current_scene = next_scene[0]
        self.session.action_handler.set_scene(self.isd.current_scene)
        current_state :State = self.session.state
        target_state :State = self.isd.current_scene.state

        # If the scene has no action mappings, then the scenario ends.
        if self.isd.current_scene.action_mappings == []:
            logging.warning("Scene has no action mappings; ending scenario.")
            self.session.end_scenario()
            return

        # Log the scene change
        logging.info("Changing to scene ID %s.", self.isd.current_scene.id)
        self.session.history.add_history(
            "Change scene",
            {"session_id": self.session.session_id,
            "scenario_id": self.id,
            "scene_id": self.isd.current_scene.id},
            target_state.to_dict() if target_state else None
        )

        '''
        Merge state from new scene into session.state.  Approach:
        0. Abort if no state to merge
        1. Replace or supplement `characters` structure based on configuration.
        2. For `supplies`, add or update any specified supplies.
        3. For everything else, replace any specified (non-None) values
           3a. Lists are copied whole (e.g., `character_importance`, `aid_delay`, `threats`).
        4. Clear hidden data (e.g., character vitals)
        '''
        # Rule 0: Abort if no state to merge
        if not target_state:
            current_state.characters = []
            return

        # Rule 1: Replace or supplement state and scene `characters` structure based on configuration.
        if self.isd.current_scene.persist_characters:
            if target_state.characters:
                replaced_character_ids = []
                persisted_characters = []
                target_character_ids = [character.id for character in target_state.characters]
                # Determine who needs to be persisted and who needs to be replaced.
                for character in previous_scene_characters:
                    if character.id in target_character_ids:
                        replaced_character_ids.append(character.id)
                    else:
                        persisted_characters.append(character)
                # Remove old versions of target characters from state.
                current_state.characters = \
                    [character for character in current_state.characters if character.id not in replaced_character_ids]
                # Replace them with the new versions, plus add new characters.
                current_state.characters.extend(deepcopy(target_state.characters))
                # Copy persisted characters (that weren't replaced) into the scene.
                target_state.characters.extend(persisted_characters)
            else:
                # No characters were specified in the scene, so inherit characters from previous scene.
                target_state.characters = previous_scene_characters
            # if removed_characters found in scene, remove those characters from the scene
            if getattr(self.isd.current_scene, 'removed_characters', None) and len(self.isd.current_scene.removed_characters) > 0:
                current_state.characters = [
                    character for character in current_state.characters
                    if character.id not in self.isd.current_scene.removed_characters
                ]
                # if the target_state includes a character that is listed in removed_characters, that is a yaml misconfiguration
                target_state.characters = [
                    character for character in target_state.characters
                    if character.id not in self.isd.current_scene.removed_characters
                ]
                filtered_out_characters = [
                    character for character in target_state.characters
                    if character.id in self.isd.current_scene.removed_characters
                ]

                if len(filtered_out_characters) > 0:
                    logging.warning("Scene configuration issue: target state includes character that was removed")
        else:
            current_state.characters = deepcopy(target_state.characters)

        # Rule 2: For `supplies`, add or update any specified supplies.
        if target_state.supplies:
            target_types = []
            current_types = []
            for target_supply in target_state.supplies:
                target_types.append(target_supply.type)
                for current_supply in current_state.supplies:
                    current_types.append(current_supply.type)
                    if target_supply.type == current_supply.type:
                        current_supply.quantity = target_supply.quantity
                        current_supply.reusable = target_supply.reusable
            new_types = [new_type for new_type in target_types if new_type not in current_types]
            new_supplies = [new_supply for new_supply in target_state.supplies if new_supply.type in new_types]
            current_state.supplies.extend(new_supplies)

        # Rule 3: For everything else, replace any specified (non-None) values.
        # Lists are copied whole (e.g., `character_importance`, `aid_delay`, `threats`).
        if target_state.unstructured:
            current_state.unstructured = target_state.unstructured
        current_state.threat_state = self.update_property(current_state.threat_state, target_state.threat_state)
        current_state.mission = self.update_property(current_state.mission, target_state.mission)
        if target_state.environment:
            current_state.environment.sim_environment = \
                self.update_property(current_state.environment.sim_environment, target_state.environment.sim_environment)
            current_state.environment.decision_environment = \
                self.update_property(current_state.environment.decision_environment, target_state.environment.decision_environment)
        
        # 4. Clear hidden data (e.g., character vitals)
        ITMScenario.clear_hidden_data(current_state)


    def update_property(self, current_state, target_state):
        if target_state:
            if not current_state:
                return target_state
            else:
                for attr in current_state.attribute_map.keys():
                    setattr(current_state, attr, getattr(target_state, attr) or getattr(current_state, attr))
        return current_state
