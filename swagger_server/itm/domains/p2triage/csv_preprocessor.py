import csv

EVALUATION_NAME = 'June2025'
WRITE_FILES = True
IGNORED_LIST = []
#IGNORED_LIST = ['MF', 'AF', 'SS', 'PS']

kdmas_info: list[dict] = [
    {'acronym': 'MF', 'full_name': 'Merit Focus', 'filename': 'June2025MeritFocus'},
    {'acronym': 'AF', 'full_name': 'Affiliation Focus', 'filename': 'June2025AffiliationFocus'},
    {'acronym': 'SS', 'full_name': 'Search vs Stay', 'filename': 'June2025SearchStay'},
    {'acronym': 'PS', 'full_name': 'Personal Safety Focus', 'filename': 'June2025PersonalSafety'}
    ]

expected_fields = ['scenario_id', 'scenario_name', 'probe_id', 'intro_text', 'probe_full_text', 'probe_question',
                   'patient_a_text', 'patient_b_text', 'pa_medical', 'pb_medical', 'pa_affiliation', 'pa_merit',
                   'pa_search', 'pa_personal_safety', 'pb_affiliation', 'pb_merit', 'pb_search', 'pb_personal_safety',
                   'choice1_text', 'choice2_text']

# Each inner list is the set of probes to include in a given scenario.
assessment_sets: dict = {
    'MF': [['21', '24', '12', '16',  '5', '10'],
           ['32', '35', '27', '48', '20',  '9'],
           ['33', '41', '40', '54', '58', '71']],
    'AF': [['18', '17', '14', '10',  '4',  '1'],
           ['24', '22', '35', '33', '44', '37'],
           ['52', '53', '42', '54', '45', '43']],
    'SS': [[ '2', '14',  '3', '40', '43', '42'],
           [ '5', '17',  '9', '44', '36', '45'],
           [ '8', '20', '13', '46', '30', '48']],
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


if __name__ == '__main__':
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
