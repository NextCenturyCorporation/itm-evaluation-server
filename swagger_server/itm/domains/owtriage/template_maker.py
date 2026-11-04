import csv
import os
import argparse
import pprint

"""
This utility takes in (slightly curated) TA1 probe data in csv format (combined AF and MF training data) and
outputs a template for a description map csv that maps the TA1-style description to something we can use in an OW3 csv.
Humans fill in the mapped descriptions and vitals, then the resulting csv will be used by two tools:
- The Open World 3 training converter, which converts existing training YAMLs into their OW3 equivalents; and
- The Open World 3 training generator, which generates an arbitrary number of OW3 training YAMLs.
The tool also performs a consistency check on the TA1 probe data to ensure that patients with the same medical
or attribute descriptions have the same medical or attribute values.

Usage: template_maker.py [-h] [-v] [-n] [-o outpath]
Options:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose logging
  -n, --no_output       Do not write output files
  -o outpath, --outpath outpath
                        Specify location for output files (no spaces)
"""

# These are constants that cannot be overridden via the command line
TRAINING_FILENAME = 'training.csv'
OUT_FILENAME = 'description_map_template.csv'

# These are default values that can be overridden via the command line
VERBOSE = False
WRITE_FILES = True
OUT_PATH = f"."

expected_fields = ['scenario_id', 'scenario_name', 'probe_id', 'intro_text', 'probe_full_text', 'probe_question',
                   'patient_a_text', 'patient_b_text', 'pa_medical', 'pb_medical',
                   'pa_affiliation', 'pa_merit', 'pb_affiliation', 'pb_merit',
                   'choice1_text', 'choice2_text', 'med_delta', 'attr_delta']


def main():
    csvfile = open(TRAINING_FILENAME, 'r', encoding='utf-8')
    reader: csv.DictReader = csv.DictReader(csvfile, fieldnames=expected_fields, restkey='junk')
    next(reader) # Skip header

    # Process the csv file creating three master lists
    af_descriptions: dict = {}
    mf_descriptions: dict = {}
    med_descriptions: dict = {}
    print(f"Processing training csv from {TRAINING_FILENAME}.")
    for row in reader:
        scenario_id = row['scenario_id']
        if not scenario_id or not row['scenario_name']:
            print("Warning: skipping scenario with no ID or name.")
            continue

        pa_text = row['patient_a_text']
        pa_med_desc = pa_text.split('\n')[0]
        pa_attr_desc = pa_text.split('\n')[1]
        pa_medical = row['pa_medical']
        pb_text = row['patient_b_text']
        pb_med_desc = pb_text.split('\n')[0]
        pb_attr_desc = pb_text.split('\n')[1]
        pb_medical = row['pb_medical']
        med_descriptions[pa_med_desc] = pa_medical
        med_descriptions[pb_med_desc] = pb_medical
        if '-MF-' in scenario_id:
            kdma = 'merit'
            kdma_desc_map = mf_descriptions
        elif '-AF-' in scenario_id:
            kdma = 'affiliation'
            kdma_desc_map = af_descriptions
        else:
            print(f"Invalid scenario_id {scenario_id}; exiting.")
            exit(1)

        # Perform consistency check on training csv
        old = kdma_desc_map.get(pa_attr_desc)
        if old:
            new = row[f"pa_{kdma}"]
            if old != new:
                print(f"That's odd, {old} is not {new}.")
        old = kdma_desc_map.get(pb_attr_desc)
        if old:
            new = row[f"pb_{kdma}"]
            if old != new:
                print(f"That's odd, {old} is not {new}.")

        # Update the appropriate map
        kdma_desc_map[pa_attr_desc] = row[f"pa_{kdma}"]
        kdma_desc_map[pb_attr_desc] = row[f"pb_{kdma}"]

    if VERBOSE:
        print("Medical Descriptions:")
        pprint.pprint(med_descriptions, indent=2)
        print("Affiliation Descriptions:")
        pprint.pprint(af_descriptions, indent=2)
        print("Merit Descriptions:")
        pprint.pprint(mf_descriptions, indent=2)

    print(f"Collected {len(mf_descriptions)} merit, {len(af_descriptions)} affiliation, and {len(med_descriptions)} medical descriptions.")

    # Construct the combined csv data
    csvdata: list = []
    for desc in med_descriptions:
        csvdata.append({'ta1_description': desc, 'near_treated_desc': '', 'far_treated_desc': '', 'far_untreated_desc': '', 'kdma': 'MED', 'pulse': 'normal', 'resp': 'normal', 'avpu': 'alert', 'value': med_descriptions[desc]})
    for desc in af_descriptions:
        csvdata.append({'ta1_description': desc, 'near_treated_desc': '', 'far_treated_desc': '', 'far_untreated_desc': '', 'kdma': 'AF', 'pulse': '', 'resp': '', 'avpu': '', 'value': af_descriptions[desc]})
    for desc in mf_descriptions:
        csvdata.append({'ta1_description': desc, 'near_treated_desc': '', 'far_treated_desc': '', 'far_untreated_desc': '', 'kdma': 'MF', 'pulse': '', 'resp': '', 'avpu': '', 'value': mf_descriptions[desc]})

    # Write the description template to a csv file
    print(f"{'NOT ' if not WRITE_FILES else ''}Writing {len(csvdata)} entries to {OUT_PATH}{os.sep}{OUT_FILENAME}.")
    if WRITE_FILES:
        os.makedirs(OUT_PATH, exist_ok=True)
        fieldnames = ['ta1_description', 'near_treated_desc', 'far_treated_desc', 'far_untreated_desc', 'kdma', 'pulse', 'resp', 'avpu', 'value']
        with open(f"{OUT_PATH}{os.sep}{OUT_FILENAME}", 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csvdata)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Converts TA1 probe data into a template for a description map csv for use in other utilities.')
    parser.add_argument('-v', '--verbose', action='store_true', required=False, default=False,
                        help='Verbose logging')
    parser.add_argument('-n', '--no_output', action='store_true', required=False, default=False,
                        help='Do not write output files')
    parser.add_argument('-o', '--outpath', required=False, metavar='outpath',
                        help='Specify location for output files (no spaces)')

    args = parser.parse_args()
    if args.verbose:
        VERBOSE = True
    if args.no_output:
        WRITE_FILES = False
    if args.outpath:
        OUT_PATH = args.outpath
    main()
