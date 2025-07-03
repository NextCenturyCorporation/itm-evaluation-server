import yaml
import csv
import os
import argparse

# These are constants that cannot be overridden via the command line
EVALUATION_NAME = 'July2025'
TA1_NAME = 'adept'

# These are default values that can be overridden via the command line
FULL_EVAL = True
REDACT_EVAL = False
VERBOSE = False
WRITE_FILES = True
OUT_PATH = f"swagger_server/itm/data/{EVALUATION_NAME.lower()}/scenarios"
IGNORED_LIST = []

kdmas_info: list[dict] = [
    {'acronym': 'MF', 'full_name': 'Merit Focus', 'filename': f'{EVALUATION_NAME}MeritFocus'},
    {'acronym': 'AF', 'full_name': 'Affiliation Focus', 'filename': f'{EVALUATION_NAME}AffiliationFocus'},
    {'acronym': 'SS', 'full_name': 'Search vs Stay', 'filename': f'{EVALUATION_NAME}SearchStay'},
    {'acronym': 'PS', 'full_name': 'Personal Safety Focus', 'filename': f'{EVALUATION_NAME}PersonalSafety'},
    {'acronym': 'AF-MF', 'full_name': 'Affiliation Focus Set', 'filename': f'{EVALUATION_NAME}-AF-MF'},
    {'acronym': 'OW', 'full_name': 'Open World Desert', 'filename': f'{EVALUATION_NAME}-OW-desert'},
    {'acronym': 'OW', 'full_name': 'Open World Urban', 'filename': f'{EVALUATION_NAME}-OW-urban'}
    ]

expected_fields = ['scenario_id', 'scenario_name', 'probe_id', 'intro_text', 'probe_full_text', 'probe_question',
                   'patient_a_text', 'patient_b_text', 'pa_medical', 'pb_medical', 'pa_affiliation', 'pa_merit',
                   'pa_search', 'pa_personal_safety', 'pb_affiliation', 'pb_merit', 'pb_search', 'pb_personal_safety',
                   'choice1_text', 'choice2_text']

def get_kdma_base(acronym, probe_id: str) -> str:
    match acronym:
        case 'AF':
            return 'affiliation'
        case 'MF':
            return 'merit'
        case 'PS':
            return 'personal_safety'
        case 'SS':
            return 'search'
        case _: # Handle multi-kdma case
            if '-AF-' in probe_id:
                return 'affiliation'
            if '-MF-' in probe_id:
                return 'merit'
            if '-PS-' in probe_id:
                return 'personal_safety'
            if '-SS-' in probe_id:
                return 'search'
    print(f"Could not derive KDMA base from acronym {acronym} or probe ID {probe_id}! Exiting.")
    exit(1)

def make_state(row: dict, acronym: str, training: str, first_row: str = False) -> dict:
    character_list: list = []
    attribute_base = get_kdma_base(acronym, row['probe_id'])
    character: dict = {'id': 'Patient A', 'name': 'Patient A', 'unstructured': row['patient_a_text']}
    if training or not REDACT_EVAL:
        character.update({'medical_condition': float(row['pa_medical'])})
        character.update({'attribute_rating': float(row[f"pa_{attribute_base}"])})
    character_list.append(character)
    if 'safety' not in attribute_base:
        character = {'id': 'Patient B', 'name': 'Patient B', 'unstructured': row['patient_b_text']}
        if training or not REDACT_EVAL:
            character.update({'medical_condition': float(row['pb_medical'])})
            character.update({'attribute_rating': float(row[f"pb_{attribute_base}"])})
        character_list.append(character)
    state: dict = {'unstructured': row['intro_text'] if first_row else row['probe_full_text'], 'characters': character_list}

    # Hack to make TA2's life easier.  TBD remove...
    threats = []
    threat_state = {'unstructured': row['intro_text'], 'threats': threats}
    if not first_row:
        state.update({'threat_state': threat_state})

    return state


def make_mappings(row: dict, acronym: str, training: bool) -> list:
    mappings: list = []

    # Process mapping #1
    choice_text: str = row['choice1_text']
    action_id: str = choice_text.lower().replace(' ', '_')
    probe_id: str = row['probe_id']
    choice_id: str = f"Response {probe_id.split()[1]}-A"
    mapping: dict = {'action_id': action_id, 'action_type': 'TREAT_PATIENT', 'unstructured': choice_text,
                     'character_id': 'Patient A', 'probe_id': probe_id, 'choice': choice_id}
    if training or not REDACT_EVAL:
        attribute_base = get_kdma_base(acronym, probe_id)
        kdma_assoc: dict = {'medical': float(row['pa_medical']), attribute_base: float(row[f"pa_{attribute_base}"])}
        mapping['kdma_association'] = kdma_assoc
    mappings.append(mapping)

    # Process mapping #2
    choice_text = row['choice2_text']
    action_id = choice_text.lower().replace(' ', '_')
    choice_id = f"Response {probe_id.split()[1]}-B"

    match acronym:
        case 'AF' | 'MF':
            action_type = 'TREAT_PATIENT'
        case 'PS':
            action_type = 'END_SCENE'
        case 'SS':
            action_type = 'SEARCH'
        case _: # Handle multi-kdma case
            if '-AF-' in probe_id or '-MF-' in probe_id:
                action_type = 'TREAT_PATIENT'
            elif '-PS-' in probe_id:
                action_type = 'END_SCENE'
            elif '-SS-' in probe_id:
                action_type = 'SEARCH'
            else:
                print(f"Could not derive action type from probe ID {probe_id}! Exiting.")
                exit(1)

    mapping = {'action_id': action_id, 'action_type': action_type, 'unstructured': choice_text,
               'probe_id': probe_id, 'choice': choice_id}
    if training or not REDACT_EVAL:
        attribute_base = get_kdma_base(acronym, probe_id)
        kdma_assoc: dict = {'medical': float(row['pb_medical']), attribute_base: float(row[f"pb_{attribute_base}"])}
        mapping['kdma_association'] = kdma_assoc
    if acronym in ['AF', 'MF', 'AF-MF', 'OW']:
        mapping['character_id'] = 'Patient B'
    mappings.append(mapping)

    return mappings


def get_scene(row: dict, acronym: str, training: bool) -> dict:
    probe_id: str = row['probe_id']
    probe_config: list = [{'description': row['probe_question']}]
    return {'id': probe_id, 'next_scene': 'placeholder', 'end_scene_allowed': acronym == 'PS', 'probe_config': probe_config,
            'state': make_state(row, acronym, training), 'action_mapping': make_mappings(row, acronym, training),
            'transitions': {'probes': [probe_id]}}


def process_scenario(reader: csv.DictReader, acronym: str, first_row: dict) -> dict | str:
    if not first_row:
        first_row: dict = next(reader)

    scenario_name = str(first_row['scenario_name'])
    training = 'Set B' in scenario_name
    data: dict = {'id': first_row['scenario_id'], 'name': scenario_name, 'state': make_state(first_row, acronym, training, True)}
    scenes: list = []
    scene = get_scene(first_row, acronym, training)
    if VERBOSE:
        print(f"Adding scene {scene['id']}")
    scenes.append(scene)

    more_data = False
    for row in reader:
        if not row['scenario_id'] or not row['scenario_name']:
            continue # Skip scenarios with no ID or name
        if str(row['scenario_name']) != scenario_name:
            more_data = True
            break # Got to the first line of the next scenario
        scene: dict = get_scene(row, acronym, training)
        if VERBOSE:
            print(f"Adding scene {scene['id']}")
        scenes.append(scene)

    data['scenes'] = scenes
    return data, row if more_data else None


def set_next_scene(scenes: list):
    num_scenes = len(scenes)
    for scene_ctr in range(num_scenes):
        if scene_ctr < num_scenes-1:
            if VERBOSE:
                print(f"Setting scene {scenes[scene_ctr]['id']} next_scene to {scenes[scene_ctr+1]['id']}")
            scenes[scene_ctr]['next_scene'] = scenes[scene_ctr+1]['id']
    scenes[-1]['next_scene'] = '__END_SCENARIO__'


def main():
    for kdma_info in kdmas_info:
        acronym = kdma_info['acronym']
        if acronym in IGNORED_LIST:
            continue
        if acronym == 'OW' and (REDACT_EVAL or not FULL_EVAL):
            continue

        full_name = kdma_info['full_name']
        filename = f"{kdma_info['filename']}.csv" if FULL_EVAL else f"{kdma_info['filename']}_evalset.csv"
        csvfile = open(filename, 'r', encoding='utf-8')
        reader: csv.DictReader = csv.DictReader(csvfile, fieldnames=expected_fields, restkey='junk')
        next(reader) # Skip header

        print(f"Processing {full_name} ({acronym}) from {filename}.")
        train_scenario_num = '' # Training probes are always put in a single file, so no numeral
        eval_scenario_num = '' if FULL_EVAL else 1  # Subset eval breaks scenarios up into sets, so use numeral
        data: dict = None
        next_row = None
        more_data = True
        # Process the csv file writing out all YAML files
        while more_data:
            data, next_row = process_scenario(reader, acronym, next_row)
            more_data = next_row is not None
            if full_name not in data['name']:
                print(f"KDMA mismatch?  {full_name} doesn't match scenario name {data['name']}.  Exiting.")
                exit(1)
            if 'train' in data['id']:
                outfile = f"{EVALUATION_NAME.lower()}-{TA1_NAME}-train-{acronym}{train_scenario_num}.yaml"
                train_scenario_num = 2 if not train_scenario_num else train_scenario_num + 1
            elif 'eval' in data['id']:
                redact_string = '_redacted' if REDACT_EVAL else ''
                outfile = f"{EVALUATION_NAME.lower()}-{TA1_NAME}-eval-{acronym}{eval_scenario_num}{redact_string}.yaml"
                eval_scenario_num = 2 if not eval_scenario_num else eval_scenario_num + 1
            else: # Open World
                environment = 'desert' if 'Desert' in kdma_info['full_name'] else 'urban'
                outfile = f"{EVALUATION_NAME.lower()}-OW-{environment}.yaml"

            # Go back and add next_scene property now that we have everything
            set_next_scene(data['scenes'])

            # Write the data to a YAML file using dump() function
            print(f"{'NOT ' if not WRITE_FILES else ''}Writing {len(data['scenes'])} probes to {OUT_PATH}{os.sep}{outfile}.")
            if WRITE_FILES:
                os.makedirs(OUT_PATH, exist_ok=True)
                with open(f"{OUT_PATH}{os.sep}{outfile}", 'w', encoding='utf-8') as file:
                    yaml.dump(data, file, sort_keys=False, indent=2)

        csvfile.close()

    print(f"All files {'NOT ' if not WRITE_FILES else ''}created.  Exiting.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts TA1 csvs to scenario YAML files.')
    parser.add_argument('-s', '--subset', action='store_true', required=False, default=False,
                        help='Generate the assessment subset evaluation files')
    parser.add_argument('-r', '--redact', action='store_true', required=False, default=False,
                        help='Generate redacted evaluation files')
    parser.add_argument('-v', '--verbose', action='store_true', required=False, default=False,
                        help='Verbose logging')
    parser.add_argument('-n', '--no_output', action='store_true', required=False, default=False,
                        help='Do not write output files')
    parser.add_argument('-o', '--outpath', required=False, metavar='outpath',
                        help='Specify location for output files (no spaces)')
    parser.add_argument('-i', '--ignore', nargs='+', metavar='ignore', required=False, type=str,
                        help="Acronyms of attributes to ignore (AF, MF, PS, SS, AF-MF)")

    args = parser.parse_args()
    if args.subset:
        FULL_EVAL = False
    if args.redact:
        REDACT_EVAL = True
    if args.verbose:
        VERBOSE = True
    if args.no_output:
        WRITE_FILES = False
    if args.outpath:
        OUT_PATH = args.outpath
    if args.ignore:
        IGNORED_LIST = args.ignore
    main()
