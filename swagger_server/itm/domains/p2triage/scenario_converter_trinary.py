"""
Convert from CSV to scenario YAMLs.

Example invocation:
python -m pip install PyYAML
python scenario_converter_trinary.py
"""
import argparse
import csv
import os
import pathlib
import random
import re
import typing

import yaml

# These are constants that cannot be overridden via the command line
DEFAULT_EVALUATION_NAME = 'June2026'
TA1_NAME = 'adept'
SHUFFLE_SEED: typing.Final[int | None] = 1 # set to an integer if you want repeatable shuffle, None means non-repeatable shuffle. (not used if SHUFFLE_SCENES is False)

# These are default values that can be overridden via the command line
REDACT_EVAL = False
VERBOSE = False
EVALUATION_NAME = DEFAULT_EVALUATION_NAME
WRITE_FILES = True
OUT_PATH = f"out"
CSV_FILE_OVERRIDES: dict[str, list[str]] = {}
IGNORED_LIST = ['MF', 'SS', 'SB', 'OW'] # Process all configured CSVs by default; use --ignore to skip any acronym
SHUFFLE_SCENES = True  # True means randomize the scene order of certain scenarios


kdmas_info: list[dict] = [
    {'acronym': 'MF', 'full_name': 'Merit Focus', 'filename': f'{EVALUATION_NAME}MeritFocusTrinary'},
    {'acronym': 'AF', 'full_name': 'Affiliation Focus', 'filename': f'{EVALUATION_NAME}AffiliationFocusTrinary'},
    {'acronym': 'SS', 'full_name': 'Search vs Stay', 'filename': f'{EVALUATION_NAME}SearchStayTrinary'},
    {'acronym': 'PS', 'full_name': 'Personal Safety Focus', 'filename': f'{EVALUATION_NAME}PersonalSafetyTrinary'},
    {'acronym': 'SB', 'full_name': 'Subpopulation', 'filename': f'{EVALUATION_NAME}Subpopulation'},
    {'acronym': 'OW', 'full_name': 'Open World Desert', 'filename': f'{EVALUATION_NAME}-OW-desert2'},
    {'acronym': 'OW', 'full_name': 'Open World Urban', 'filename': f'{EVALUATION_NAME}-OW-urban2'}
    ]

kdma_mapping: dict = {'AF': 'affiliation', 'MF': 'merit', 'SS': 'search', 'PS': 'personal_safety', 'SB': 'subpopulation'}

expected_fields = ['scenario_id', 'scenario_name', 'probe_id', 'intro_text', 'probe_full_text', 'probe_question',
                   'patient_a_text', 'patient_b_text', 'pa_treated', 'pb_treated', 'pa_medical', 'pb_medical',
                   'pa_affiliation', 'pa_merit', 'pa_search', 'pa_personal_safety', 'pb_affiliation', 'pb_merit',
                   'pb_search', 'pb_personal_safety', 'choice1_text', 'choice2_text']

REQUIRED_NON_EMPTY_FIELDS_COMMON: typing.Final[tuple[str, ...]] = (
    'scenario_id',
    'scenario_name',
    'probe_id',
    'intro_text',
    'probe_full_text',
    'probe_question',
    'patient_a_text',
    'patient_b_text',
    'pa_medical',
    'pb_medical',
    'choice1_text',
    'choice2_text',
)

REQUIRED_NON_EMPTY_FIELDS_TRINARY_ONLY: typing.Final[tuple[str, ...]] = (
    'patient_c_text',
    'pc_medical',
    'choice3_text',
)

ow_char_info: dict

def get_kdma_bases(acronym, probe_id: str):
    kdmas = []
    parts: list = probe_id.split('-')
    if len(parts) == 1: # single kdma, e.g. "Probe 23"
        kdma = kdma_mapping.get(acronym)
        if kdma:
            kdmas.append(kdma)

    # multi-kdma, e.g. "July2025-AF-eval.Probe 21" or "Sept2025-PS-AF-eval.Probe 12"
    for part in parts:
        if part in kdma_mapping.keys():
            kdmas.append(kdma_mapping[part])

    if len(kdmas) == 0:
        if 'Fake' not in probe_id:
            print(f"WARNING: could not derive KDMA base from acronym {acronym} or probe ID {probe_id}; assuming merit.")
        kdmas.append('merit')

    return kdmas


def safe_float(value, default: float = 0.0) -> float:
    """Convert spreadsheet values to floats, treating blanks/missing values as default."""
    if value is None or value == '':
        return default
    return float(value)


def safe_int(value, default: int = 0) -> int:
    if value is None or value == '':
        return default
    return int(float(value))


def row_value(row: dict, key: str, default: str = ''):
    value = row.get(key, default)
    return default if value is None else value


def letters_from_row(row: dict) -> list[str]:
    """Return patient/choice letters present in either old binary or new trinary CSVs."""
    letters = []
    for letter in ['a', 'b', 'c']:
        if (row_value(row, f'patient_{letter}_text') or
                row_value(row, f'p{letter}_medical') or
                row_value(row, f'p{letter}_affiliation') or
                row_value(row, f'p{letter}_merit') or
                row_value(row, f'p{letter}_search') or
                row_value(row, f'p{letter}_personal_safety')):
            letters.append(letter)
    return letters or ['a', 'b']


def is_ps_wait_option(row: dict, acronym: str, letter: str) -> bool:
    """The trinary PS files encode the third option as waiting/staying safe, not Patient C."""
    if letter != 'c':
        return False
    probe_id = row_value(row, 'probe_id')
    return acronym == 'PS' or '-PS-' in probe_id


def make_state(row: dict, acronym: str, training: bool, first_row: bool = False) -> dict:
    character_list: list = []
    attribute_base = get_kdma_bases(acronym, row['probe_id'])[0]

    for letter in letters_from_row(row):
        if is_ps_wait_option(row, acronym, letter):
            continue
        patient_label = f"Patient {letter.upper()}"
        patient_text = row_value(row, f'patient_{letter}_text')
        if not patient_text:
            continue
        character: dict = {'id': patient_label, 'name': patient_label, 'unstructured': patient_text}
        if training or not REDACT_EVAL:
            character.update({'medical_condition': safe_float(row_value(row, f'p{letter}_medical'))})
            attr_value = row_value(row, f"p{letter}_{attribute_base}")
            if attr_value != '':
                character.update({'attribute_rating': safe_float(attr_value)})
        character_list.append(character)

    state: dict = {'unstructured': row['intro_text'] if first_row else row['probe_full_text'], 'characters': character_list}

    # Hack to make TA2's life easier.  TBD remove...
    if 'Open World' not in row['scenario_name']:
        threats = []
        threat_state = {'unstructured': row['intro_text'], 'threats': threats}
        if not first_row:
            state.update({'threat_state': threat_state})
    else: # save character info for OW scenarios
        for index, char in enumerate(character_list):
            patient_name = f"Patient {len(ow_char_info) + 1}"
            unstructured: str = char['unstructured']
            char_name = (unstructured.split(';')[-1]).strip()
            unstructured = unstructured[0:unstructured.rindex(';')]
            if char_name not in ow_char_info.keys(): # Have we added this patient yet?
                letter = chr(ord('a') + index)
                char_info: dict = {'id': patient_name, 'name': patient_name, 'unstructured': unstructured,
                                'unstructured_posttreatment': row_value(row, f'p{letter}_treated'),
                                'medical_condition': char['medical_condition']}
                ow_char_info[char_name] = char_info

    return state

def default_choice_text(row: dict, acronym: str, letter: str) -> str:
    if is_ps_wait_option(row, acronym, letter):
        return 'Wait in your current location'
    return f"Treat Patient {letter.upper()}"


def action_type_for_choice(row: dict, acronym: str, letter: str, num_choices: int) -> str:
    probe_id = row_value(row, 'probe_id')

    if acronym == 'PS' or '-PS-' in probe_id:
        # Old binary PS probes used choice B as wait/end-scene. New trinary PS probes use
        # A/B as treat-patient options and C as the wait/end-scene option.
        return 'END_SCENE' if (letter == 'c' or (num_choices < 3 and letter == 'b')) else 'TREAT_PATIENT'
    if acronym == 'SS' or '-SS-' in probe_id:
        return 'SEARCH'
    return 'TREAT_PATIENT'


def make_kdma_assoc(row: dict, acronym: str, probe_id: str, letter: str) -> dict:
    kdma_assoc: dict = {'medical': safe_float(row_value(row, f'p{letter}_medical'))}
    attribute_bases = get_kdma_bases(acronym, probe_id) if acronym != 'SB' else kdma_mapping.values()
    for base in attribute_bases:
        value = row_value(row, f"p{letter}_{base}")
        if value != '':
            kdma_assoc[base] = safe_float(value) if base != 'subpopulation' else safe_int(value)
    return kdma_assoc


def choice_number(row: dict, letter: str) -> int:
    return ord(letter) - ord('a') + 1


def make_mappings(row: dict, acronym: str, training: bool) -> list:
    mappings: list = []
    probe_id: str = row['probe_id']
    letters = letters_from_row(row)
    num_choices = max(choice_number(row, letter) for letter in letters)

    for letter in letters:
        choice_num = choice_number(row, letter)
        choice_text: str = row_value(row, f'choice{choice_num}_text') or default_choice_text(row, acronym, letter)
        action_id: str = choice_text.lower().replace(' ', '_')
        choice_id: str = f"Response {probe_id.split()[1]}-{letter.upper()}"
        action_type = action_type_for_choice(row, acronym, letter, num_choices)

        mapping: dict = {'action_id': action_id, 'action_type': action_type, 'unstructured': choice_text,
                         'probe_id': probe_id, 'choice': choice_id}

        if action_type == 'TREAT_PATIENT':
            mapping['character_id'] = f"Patient {letter.upper()}"

        if training or not REDACT_EVAL:
            mapping['kdma_association'] = make_kdma_assoc(row, acronym, probe_id, letter)

        mappings.append(mapping)

    return mappings

def get_scene(row: dict, acronym: str, training: bool, scene_num=1) -> dict:
    probe_id: str = row['probe_id']
    scene_id = f"Scene {scene_num}"
    probe_config: list = [{'description': row['probe_question']}]
    return {'id': scene_id, 'next_scene': 'placeholder', 'end_scene_allowed': 'PS' == acronym or '-PS-' in probe_id, 'probe_config': probe_config,
            'state': make_state(row, acronym, training), 'action_mapping': make_mappings(row, acronym, training),
            'transitions': {'probes': [probe_id]}}


def _csv_has_trinary_columns(fieldnames: typing.Iterable[str] | None) -> bool:
    """
    :param fieldnames: Header names from the CSV file.
    :return: True when the new-format CSV contains the required Patient C / choice 3 columns.
    """
    field_set = set(fieldnames or [])
    return set(REQUIRED_NON_EMPTY_FIELDS_TRINARY_ONLY).issubset(field_set)


def _is_trinary_input_file(filename: str, fieldnames: typing.Iterable[str] | None = None) -> bool:
    """
    Determine whether a new-format CSV is trinary.

    New binary files are not required to contain ``binary`` in
    their filenames, so the header is the source of truth.  The filename check
    exists only as a helpful fallback for generated trinary filenames such as
    ``June2026PersonalSafetyTrinary.csv``.
    """
    filename_lower = os.path.basename(filename).lower()
    if 'trinary' in filename_lower:
        return True
    return _csv_has_trinary_columns(fieldnames)


def input_format_tag(filename: str, fieldnames: typing.Iterable[str] | None = None) -> str:
    """
    :return: The output filename tag for the CSV's choice format.
    """
    return 'trinary' if _is_trinary_input_file(filename, fieldnames) else 'binary'


def _required_non_empty_fields_for_file(filename: str, fieldnames: typing.Iterable[str] | None = None) -> tuple[str, ...]:
    """
    :param filename: The CSV filename.
    :param fieldnames: Header names from the CSV file.
    :return: Required non-empty fields for this CSV format.
    """
    if _is_trinary_input_file(filename, fieldnames):
        return REQUIRED_NON_EMPTY_FIELDS_COMMON + REQUIRED_NON_EMPTY_FIELDS_TRINARY_ONLY
    return REQUIRED_NON_EMPTY_FIELDS_COMMON


def _is_non_data_csv_row(row: dict) -> bool:
    """
    :param row: A CSV row.
    :return: True if the row has no scenario_id and no scenario_name.
    """
    scenario_id = str(row.get('scenario_id', '')).strip()
    scenario_name = str(row.get('scenario_name', '')).strip()
    return scenario_id == '' and scenario_name == ''


def _validate_required_cells(
    row: dict,
    row_num: int,
    filename: str,
    fieldnames: typing.Iterable[str] | None = None,
) -> None:
    """
    Validate that required CSV cells are populated.

    Rows without both scenario_id and scenario_name are considered non-data rows
    and should be skipped before this function is called.

    :param row: A CSV row.
    :param row_num: The 1-based CSV row number.
    :param filename: The filename, for error reporting.
    :param fieldnames: Header names from the CSV file.
    """
    missing_fields = [
        field
        for field in _required_non_empty_fields_for_file(filename, fieldnames)
        if str(row.get(field, '')).strip() == ''
    ]

    forbidden_fields = []
    if not _is_trinary_input_file(filename, fieldnames):
        forbidden_fields = [
            field
            for field in REQUIRED_NON_EMPTY_FIELDS_TRINARY_ONLY
            if str(row.get(field, '')).strip() != ''
        ]

    if missing_fields or forbidden_fields:
        raise ValueError(
            "CSV row is missing required values.\n"
            f"filename={filename!r}\n"
            f"row_num={row_num}\n"
            f"missing_fields={missing_fields!r}\n"
            f"forbidden_fields={forbidden_fields!r}\n"
            f"scenario_id={row.get('scenario_id', '')!r}\n"
            f"scenario_name={row.get('scenario_name', '')!r}\n"
            f"probe_id={row.get('probe_id', '')!r}"
        )
    return None


def parse_new_scenario_id(scenario_id: str, expected_acronym: str) -> tuple[str, str, bool]:
    """
    Parse a new-format scenario_id.

    Expected examples::

        June2026-PS1-assess
        June2026-PS-eval
        June2026-AF-train-trinary

    :return: (kdma_part, split, is_trinary_id), where kdma_part is e.g.
        ``PS1`` or ``AF``.
    """
    pattern = re.compile(
        r'^(?P<evaluation>[^-]+)-'
        r'(?P<kdma_part>(?P<acronym>[A-Z]+)\d*)-'
        r'(?P<split>train|eval|observe|assess)'
        r'(?P<trinary>-trinary)?$'
    )
    match = pattern.match(scenario_id)
    if not match:
        raise ValueError(
            "CSV scenario_id does not match the new June2026 convention.\n"
            f"scenario_id={scenario_id!r}\n"
            "Expected something like 'June2026-PS1-assess' or "
            "'June2026-AF-eval-trinary'."
        )

    acronym = match.group('acronym')
    if acronym != expected_acronym:
        raise ValueError(
            "CSV scenario_id acronym does not match the CSV being processed.\n"
            f"scenario_id={scenario_id!r}\n"
            f"expected_acronym={expected_acronym!r}\n"
            f"actual_acronym={acronym!r}"
        )

    return match.group('kdma_part'), match.group('split'), bool(match.group('trinary'))


def output_filename_for_scenario(
    *,
    scenario_id: str,
    acronym: str,
    format_tag: str,
    redact_string: str,
) -> str:
    """
    Build the YAML filename directly from the new-format scenario_id.

    Binary scenarios omit the arity tag. Trinary scenarios include
    ``trinary`` in the filename.
    """
    kdma_part, split, _scenario_id_is_trinary = parse_new_scenario_id(
        scenario_id=scenario_id,
        expected_acronym=acronym,
    )
    arity_part = "trinary-" if format_tag == "trinary" else ""
    return f"{EVALUATION_NAME.lower()}-{TA1_NAME}-{split}-{arity_part}{kdma_part}{redact_string}.yaml"


def group_rows_by_scenario(reader: csv.DictReader, filename: str) -> list[list[dict]]:
    """
    Group CSV rows by scenario_id/scenario_name while preserving first-seen order.

    Rows for the same scenario do not need to be contiguous, but a scenario is
    assumed not to be spread across multiple CSV files.

    :param reader: The CSV reader.
    :return: One list of rows per unique scenario_id/scenario_name pair.
    """
    scenario_rows_by_key: dict[tuple[str, str], list[dict]] = {}
    fieldnames = reader.fieldnames or []

    for row_num, row in enumerate(reader, start=2):  # Header is row 1.
        if _is_non_data_csv_row(row):
            continue
        _validate_required_cells(row=row, row_num=row_num, filename=filename, fieldnames=fieldnames)

        scenario_id = row.get('scenario_id', '').strip()
        scenario_name = row.get('scenario_name', '').strip()

        if not scenario_id or not scenario_name:
            raise ValueError(
                "CSV row has only one of scenario_id/scenario_name populated.\n"
                f"row_num={row_num}\n"
                f"scenario_id={scenario_id!r}\n"
                f"scenario_name={scenario_name!r}"
            )

        scenario_key = (scenario_id, scenario_name)
        scenario_rows_by_key.setdefault(scenario_key, []).append(row)

    return list(scenario_rows_by_key.values())


def make_scenario_uid(scenario_id: str, scenario_name: str) -> str:
    """
    Return the scenario ID supplied by the new-format CSV.

    The new CSV convention makes scenario_id unique directly, so the converter no
    longer appends scenario_name to create a synthetic UID.  The scenario_name
    parameter is kept because tests and integration checks use this helper as the
    single place that defines CSV-row-to-YAML-scenario identity.
    """
    return scenario_id.strip()


def process_scenario(rows: list[dict], acronym: str, full_name: str) -> dict:
    """
    Build one scenario YAML data structure from all rows for one scenario.

    :param rows: All CSV rows for one scenario_id/scenario_name pair.
    :param acronym: The KDMA acronym being processed.
    :param full_name: The full display name for the KDMA.
    :return: The scenario YAML data structure.
    """
    if not rows:
        raise ValueError("Cannot process an empty scenario row list.")

    first_row = rows[0]
    csv_scenario_id = str(first_row['scenario_id'])
    scenario_name = str(first_row['scenario_name'])
    scenario_id = make_scenario_uid(csv_scenario_id, scenario_name)
    scenario_key = (csv_scenario_id, scenario_name)

    for row in rows:
        row_key = (str(row['scenario_id']), str(row['scenario_name']))
        if row_key != scenario_key:
            raise ValueError(
                "Internal error: process_scenario received mixed scenario rows.\n"
                f"expected={scenario_key!r}\n"
                f"actual={row_key!r}"
            )

    training = 'Training' in scenario_name
    if 'Observation Set' in scenario_name:
        data: dict = {
            'id': scenario_id,
            'name': scenario_name,
            "alt_id": scenario_id.replace(acronym, ''),
            "alt_name": scenario_name.replace(f'{full_name} ', ''),
            'state': make_state(first_row, acronym, training, True),
        }
    elif ('Evaluation Set' in scenario_name or 'Eval' in scenario_name) and 'Full Evaluation' not in scenario_name:
        data: dict = {
            'id': scenario_id,
            'name': scenario_name,
            "alt_id": scenario_id.replace(f'-{acronym}-', '-'),
            "alt_name": scenario_name.replace(f'{full_name} ', ''),
            'state': make_state(first_row, acronym, training, True),
        }
    elif 'Open World' in scenario_name and 'Part' in scenario_name:
        data: dict = {
            'id': scenario_id,
            'name': scenario_name,
            'first_scene': 'treat_and_tag',
            'state': make_state(first_row, acronym, False, True),
        }
    else:
        data: dict = {
            'id': scenario_id,
            'name': scenario_name,
            'state': make_state(first_row, acronym, training, True),
        }

    scenes: list = []
    for scene_num, row in enumerate(rows, start=1):
        scene = get_scene(row, acronym, training, scene_num)
        if VERBOSE:
            print(f"Adding scene {scene['id']}")
        scenes.append(scene)

    data['scenes'] = scenes
    return data


def set_next_scene(scenes: list):
    num_scenes = len(scenes)
    for scene_ctr in range(num_scenes):
        if scene_ctr < num_scenes-1:
            if VERBOSE:
                print(f"Setting scene {scenes[scene_ctr]['id']} next_scene to {scenes[scene_ctr+1]['id']}")
            scenes[scene_ctr]['next_scene'] = scenes[scene_ctr+1]['id']
    scenes[-1]['next_scene'] = '__END_SCENARIO__'


"""
    Add (mostly fixed) tag+treat and evac scenes
"""
def add_ow_scenes(data: dict):
    if VERBOSE:
        print(ow_char_info)

    # Add treat_and_tag scene
    characters: list = [char for char in ow_char_info.values()]
    action_mapping: list = []
    action_mapping.append({'action_id': 'treat_patient', 'action_type': 'TREAT_PATIENT', 'unstructured': "Treat a Patient", 'repeatable': True})
    action_mapping.append({'action_id': 'tag_patient', 'action_type': 'TAG_CHARACTER', 'unstructured': "Place a triage tag on a Patient", 'repeatable': True})
    state = {'unstructured': data['state']['unstructured'] + " Medevac is inbound. Please treat and tag patients all patients, then end the scene when you are done.",
             'characters': characters}
    treat_and_tag_scene = {'id': 'treat_and_tag', 'next_scene': 'evac_decision', 'end_scene_allowed': True, 'restricted_actions': ['MOVE_TO_EVAC'],
                           'state': state, 'action_mapping': action_mapping, 'transitions': {'elapsed_time_gt': 999}}
    data['scenes'].append(treat_and_tag_scene)

    # Add evac_decision scene
    action_mapping = []
    action_mapping.append({'action_id': 'evac_patient', 'action_type': 'MOVE_TO_EVAC', 'unstructured': "Move a Patient to Medevac", 'repeatable': True})
    state = {'unstructured': "Medevac has arrived. Three casualty capacity only. Whom are you selecting for transport?"}
    evac_scene = {'id': 'evac_decision', 'next_scene': '__END_SCENARIO__', 'end_scene_allowed': False, 'restricted_actions': ['TREAT_PATIENT', 'TAG_CHARACTER'],
                           'persist_characters': True, 'state': state, 'action_mapping': action_mapping, 'transitions': {'elapsed_time_gt': 299}}
    data['scenes'].append(evac_scene)



def main():
    if SHUFFLE_SEED is not None:
        random.seed(SHUFFLE_SEED)

    eval_filenum = 0
    for kdma_info in kdmas_info:
        acronym = kdma_info['acronym']
        if acronym in IGNORED_LIST:
            continue

        full_name = kdma_info['full_name']
        filenames = CSV_FILE_OVERRIDES.get(acronym, [f"{kdma_info['filename']}.csv"])

        for filename in filenames:
            with open(filename, 'r', encoding='utf-8-sig') as csvfile:
                reader: csv.DictReader = csv.DictReader(csvfile)
                format_tag = input_format_tag(filename=filename, fieldnames=reader.fieldnames)

                print(f"Processing {full_name} ({acronym}) from {filename}.")
                scenario_row_groups = group_rows_by_scenario(reader=reader, filename=filename)

                for scenario_rows in scenario_row_groups:
                    global ow_char_info
                    ow_char_info = {}
                    data = process_scenario(scenario_rows, acronym, full_name)
                    redact_string = '_redacted' if REDACT_EVAL else ''
                    if full_name not in data['name'] and VERBOSE:
                        print(f"Note: {full_name} does not appear in scenario name {data['name']}; continuing.")

                    scenario_id_lower = data['id'].lower()
                    if 'train' in scenario_id_lower and REDACT_EVAL:
                        continue
                    if 'assess' in scenario_id_lower and REDACT_EVAL:
                        continue

                    if 'eval' in scenario_id_lower:
                        if 'alt_id' not in data or 'alt_name' not in data:
                            raise ValueError(
                                "CSV inconsistency: scenario classified as eval by scenario_id "
                                "but scenario_name did not match expected eval patterns.\n"
                                f"scenario_id={data['id']!r}\n"
                                f"scenario_name={data['name']!r}\n"
                                f"acronym={acronym!r}\n"
                                "Expected scenario_name to contain something like 'Eval' or 'Evaluation Set'."
                            )

                        eval_filenum += 1
                        data['alt_id'] = f"{data['alt_id']}-{eval_filenum}"
                        data['alt_name'] = f"{data['alt_name']} {eval_filenum}"

                    if 'subpopulation' in scenario_id_lower:
                        outfile = f"{EVALUATION_NAME.lower()}-{TA1_NAME}-subpopulation.yaml"
                    elif 'openworld' in scenario_id_lower or 'Open World' in data['name']:
                        environment = 'desert' if 'Desert' in kdma_info['full_name'] else 'urban'
                        outfile = f"{EVALUATION_NAME.lower()}-{environment}-openworld2{redact_string}.yaml"
                    else:
                        outfile = output_filename_for_scenario(
                            scenario_id=data['id'],
                            acronym=acronym,
                            format_tag=format_tag,
                            redact_string=redact_string,
                        )

                    if SHUFFLE_SCENES and 'train' not in scenario_id_lower and 'subpopulation' not in scenario_id_lower:
                        random.shuffle(data['scenes'])
                    set_next_scene(data['scenes'])

                    if "Open World" in data['name']:
                        add_ow_scenes(data)

                    print(f"{'NOT ' if not WRITE_FILES else ''}Writing {len(data['scenes'])} probes to {OUT_PATH}{os.sep}{outfile}.")
                    if WRITE_FILES:
                        os.makedirs(OUT_PATH, exist_ok=True)
                        with open(f"{OUT_PATH}{os.sep}{outfile}", 'w', encoding='utf-8') as file:
                            yaml.dump(data, file, sort_keys=False, indent=2)

    print(f"All files {'NOT ' if not WRITE_FILES else ''}created.  Exiting.")



def _infer_acronym_from_scenario_id(scenario_id: str) -> str | None:
    """Infer a KDMA acronym from a new-format scenario_id."""
    for part in scenario_id.split('-'):
        match = re.fullmatch(r'([A-Z]+)\d*', part)
        if match and match.group(1) in kdma_mapping:
            return match.group(1)
    return None


def _infer_acronym_from_filename(csv_path: pathlib.Path) -> str | None:
    """Infer a KDMA acronym from the new CSV filename convention."""
    normalized_name = re.sub(r'[^a-z0-9]+', '', csv_path.name.lower())

    for info in kdmas_info:
        acronym = info['acronym']
        if acronym not in kdma_mapping:
            continue

        filename_stem = re.sub(r'[^a-z0-9]+', '', info['filename'].lower())
        full_name = re.sub(r'[^a-z0-9]+', '', info['full_name'].lower())
        acronym_lower = acronym.lower()

        if (
            filename_stem in normalized_name
            or full_name in normalized_name
            or re.search(rf'(^|[^a-z]){re.escape(acronym_lower)}([^a-z]|$)', csv_path.name.lower())
        ):
            return acronym

    return None


def infer_csv_files_from_cwd() -> dict[str, list[str]]:
    """
    Scan the current working directory for new-format CSV files and infer KDMA
    acronym from scenario_id first, then from filename.

    :return: Mapping of acronym -> CSV paths.
    """
    inferred: dict[str, list[str]] = {}

    cwd = pathlib.Path.cwd()
    csv_files = list(cwd.glob("*.csv"))

    for csv_path in csv_files:
        acronym: str | None = None

        try:
            with open(csv_path, 'r', encoding='utf-8-sig', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if _is_non_data_csv_row(row):
                        continue
                    acronym = _infer_acronym_from_scenario_id(row.get('scenario_id', ''))
                    break
        except OSError as exc:
            print(f"WARNING: Could not inspect {csv_path.name}: {exc}; skipping.")
            continue

        acronym = acronym or _infer_acronym_from_filename(csv_path)

        if acronym is not None:
            inferred.setdefault(acronym, []).append(str(csv_path))
        else:
            print(f"INFO: No acronym match for {csv_path.name}; skipping.")

    return inferred


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts TA1 csvs to scenario YAML files.')
    parser.add_argument('-r', '--redact', action='store_true', required=False, default=False,
                        help='Generate redacted evaluation files')
    parser.add_argument('-v', '--verbose', action='store_true', required=False, default=False,
                        help='Verbose logging')
    parser.add_argument('-e', '--evalname', required=False, metavar='evalname', default=DEFAULT_EVALUATION_NAME,
                        help=f'Short name for evaluation (no spaces); default {DEFAULT_EVALUATION_NAME}')
    parser.add_argument('-n', '--no_output', action='store_true', required=False, default=False,
                        help='Do not write output files')
    parser.add_argument('-o', '--outpath', required=False, metavar='outpath',
                        help='Specify location for output files (no spaces)')
    parser.add_argument('-i', '--ignore', nargs='+', metavar='ignore', required=False, type=str,
                        help="Acronyms of attributes to ignore (AF, MF, PS, SS, AF-MF, PS-AF, OW)")
    parser.add_argument('-f', '--files', nargs='+', metavar='ACRONYM=CSV', required=False, type=str,
                        help='Override input CSV paths, e.g. AF=June2026AffiliationFocusTrinary.csv PS=June2026PersonalSafety.csv PS=June2026PersonalSafetyTrinary.csv')
    parser.add_argument('--no-shuffle', action='store_true', required=False, default=False,
                        help='Do not shuffle non-training, non-subpopulation scenario scenes')

    args = parser.parse_args()
    if args.redact:
        REDACT_EVAL = True
    if args.verbose:
        VERBOSE = True
    if args.evalname:
        EVALUATION_NAME = args.evalname
        OUT_PATH = OUT_PATH.replace(DEFAULT_EVALUATION_NAME.lower(), EVALUATION_NAME.lower())
        for kdma_info in kdmas_info:
            kdma_info['filename'] = kdma_info['filename'].replace(DEFAULT_EVALUATION_NAME, EVALUATION_NAME)
    if args.no_output:
        WRITE_FILES = False
    if args.outpath:
        OUT_PATH = args.outpath
    if args.ignore:
        IGNORED_LIST = args.ignore
    if args.files:
        for item in args.files:
            if '=' not in item:
                print(f"Invalid --files entry '{item}'. Expected ACRONYM=CSV.")
                exit(1)
            acronym, path = item.split('=', 1)
            CSV_FILE_OVERRIDES.setdefault(acronym, []).append(path)
    else:
        inferred = infer_csv_files_from_cwd()
        if not inferred:
            print("ERROR: No CSV files found or inferred in current directory.")
            exit(1)
        print(f"Inferred CSV mappings: {inferred}")
        CSV_FILE_OVERRIDES.update(inferred)
    if not args.ignore:  # If --ignore not provided, infer it as the complement of included acronyms
        all_acronyms = {info['acronym'] for info in kdmas_info}
        included = set(CSV_FILE_OVERRIDES.keys())
        inferred_ignore = sorted(all_acronyms - included)
        IGNORED_LIST = inferred_ignore
        print(f"Inferred IGNORED_LIST (complement of inputs): {IGNORED_LIST}")
    if args.no_shuffle:
        SHUFFLE_SCENES = False

    main()
