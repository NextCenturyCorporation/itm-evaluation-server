import csv, argparse

DEFAULT_EVALUATION_NAME = 'Sept2025'
EVALUATION_NAME = DEFAULT_EVALUATION_NAME
WRITE_FILES = True
IGNORED_LIST = ['SS']

kdmas_info: list[dict] = [
    {'acronym': 'MF', 'full_name': 'Merit Focus', 'filename': f'{EVALUATION_NAME}MeritFocus'},
    {'acronym': 'AF', 'full_name': 'Affiliation Focus', 'filename': f'{EVALUATION_NAME}AffiliationFocus'},
    {'acronym': 'SS', 'full_name': 'Search vs Stay', 'filename': f'{EVALUATION_NAME}SearchStay'},
    {'acronym': 'PS', 'full_name': 'Personal Safety Focus', 'filename': f'{EVALUATION_NAME}PersonalSafety'}
    ]

expected_fields = ['scenario_id', 'scenario_name', 'probe_id', 'intro_text', 'probe_full_text', 'probe_question',
                   'patient_a_text', 'patient_b_text', 'pa_medical', 'pb_medical', 'pa_affiliation', 'pa_merit',
                   'pa_search', 'pa_personal_safety', 'pb_affiliation', 'pb_merit', 'pb_search', 'pb_personal_safety',
                   'choice1_text', 'choice2_text']

# Each inner list is the set of probes to include in a given scenario.
assessment_sets: dict = {
    'MF': [['101',  '41', '21', '27',  '56',   '1'],
           ['102',  '43', '22', '30', '107', '109'],
           ['103',  '44', '61', '68', '108', '110']],
    'AF': [['101',  '29', '18', '15',   '9',   '5'],
           ['106',  '36', '34', '21',  '39',   '6'],
           ['107', '113', '48', '31',  '40', '111']],
    'SS': [[ '2',    '6', '13', '15',  '33',  '42'],
           [ '4',   '14', '26', '21',  '39',  '45'],
           [ '11',  '16', '38', '41',  '43',  '51']],
    'PS': [['14',  '1',  '7',  '8',  '4',  '3'],
           ['13', '16', '17', '22',  '5',  '9'],
           ['19', '20', '24', '23', '21', '11']]
    }


def process_row(out_data: list, row: dict, acronym: str, full_name: str):
    probe_num = row['probe_id'].split()[1]
    scenario_num = 1
    # If probe id is in one of the sets, then update id & name and save the row to the appropriate output bin
    for assessment_set in assessment_sets[acronym]:
        if probe_num in assessment_set:
            new_id = f"{EVALUATION_NAME}-{acronym}{scenario_num}-eval"
            update_data = {'scenario_id': new_id,
                           'scenario_name': f"{full_name} Set {scenario_num}"}
            print(f'Updating Probe {probe_num} with id {new_id} and name {f"{full_name} Set {scenario_num}"}.')
            row.update(update_data)
            out_data[scenario_num-1].append(row)
            break
        else:
            scenario_num += 1


def main():
    for kdma_info in kdmas_info:
        acronym = kdma_info['acronym']
        if acronym in IGNORED_LIST:
            continue
        full_name = kdma_info['full_name']
        filename = kdma_info['filename']
        out_filename = f"{filename}_evalset.csv"
        csv_infile = open(f"{filename}.csv", 'r', encoding='utf-8')
        csv_outfile = open(out_filename, 'w', encoding='utf-8')
        reader: csv.DictReader = csv.DictReader(csv_infile, fieldnames=expected_fields, restkey='junk')
        writer: csv.DictWriter = csv.DictWriter(csv_outfile, fieldnames=expected_fields, lineterminator='\n')
        next(reader) # Skip header
        writer.writeheader()

        print(f"Processing {full_name} ({acronym}) from {filename}.")
        out_data: list = []
        for _ in range (len(assessment_sets[acronym])):
            out_data.append([])

        for row in reader:
            scenario_id = row['scenario_id']
            if not scenario_id:
                continue # Skip scenarios with no ID
            if 'train' in scenario_id:
                continue # Skip training scenarios
            else:
                process_row(out_data, row, acronym, full_name)

        # Write out the rows in all of the bins, in order
        for bin in out_data:
            for row in bin:
                clean_row = {k: v for k, v in row.items() if k != 'junk'}
                writer.writerow(clean_row)

        num_rows = sum(len(rows) for rows in out_data)
        print(f"Wrote {num_rows} rows to {out_filename}.\n")
        csv_infile.close()
        csv_outfile.close()

    print("All files created.  Exiting.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts TA1 csvs to scenario YAML files.')
    parser.add_argument('-v', '--verbose', action='store_true', required=False, default=False,
                        help='Verbose logging')
    parser.add_argument('-e', '--evalname', required=False, metavar='evalname', default=DEFAULT_EVALUATION_NAME,
                        help=f'Short name for evaluation (no spaces); default {DEFAULT_EVALUATION_NAME}')
    parser.add_argument('-i', '--ignore', nargs='+', metavar='ignore', required=False, type=str,
                        help="Acronyms of attributes to ignore (AF, MF, PS, SS, AF-MF, PS-AF, OW)")

    args = parser.parse_args()
    if args.subset:
        FULL_EVAL = False
    if args.redact:
        REDACT_EVAL = True
    if args.verbose:
        VERBOSE = True
    if args.evalname:
        EVALUATION_NAME = args.evalname
        for kdma_info in kdmas_info:
            kdma_info['filename'] = kdma_info['filename'].replace(DEFAULT_EVALUATION_NAME, EVALUATION_NAME)
    if args.ignore:
        IGNORED_LIST = args.ignore
    main()
