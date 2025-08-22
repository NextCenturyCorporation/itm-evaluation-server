"""
Integration testing harness that atuomates dummy ADM runs.

Usage:
python run_integration_tests.py --group <group_number> --branch <branch_name> [--port <port>]

Existing Groups:
Group 1: Phase 2 testing mode - configs: DEFAULT, GROUP_TARGET, SUBSET_ONLY, FULL_NO_SUBSET, MULTI_KDMA, MULTI_KDMA_SUBSET
Group 2: Phase 2 normal mode - configs: MULTI_KDMA_FULL_NO_SUBSET, OPEN_WORLD
Group 3: Phase 1 testing mode - configs: DEFAULT, GROUP_TARGET

Making Modifications:
All modifications should be made to the GROUPS object defined below. The name of any group can be any arbitrary string. 
Each group has three parameters. The first of these is cfgs, which represents an array of configuration options that the dummy ADM will run on.
These configuration options are based on the names of configurations in the Phase 1 and Phase 2 config.ini files.
Testing is a boolean parameter. When True, this script will start the server in testing mode, disabling connection to a TA1 server. If False,
the server is started normally, which significantly increases the time taken for a dummy ADM run to complete. 
Finally, the phase parameter is an integer that specifies which phase the configurations belong to. This is important to ensuring that the dummy
ADM is run with --domain triage if the phase is 1. To make changes to the sample Groups present in this file, you can modify any of these variables above.
Ensure that any value in the cfgs array is a valid configuration option by checking against the server parameter option documentation in the README.
You can also add nw groups or delete existing ones if required. However, note that no two groups can have the same name. 
All three of the aforementioned parameters must be present in a GROUP definition for it to be valid. Missing parameters will lead to runtime errors.

Key Assumptions:
- A sibling folder "itm-evaluation-client" hosts the client repo.
- A sibling folder "evaluation_client" contains the client virtual environment with Scripts\python.exe.
- If a Phase 1 group is being tested, the 

"""

import argparse
import subprocess
import time
import requests
import os
import sys
import logging

GROUPS = {
    '1': {
        'cfgs': ["DEFAULT", "GROUP_TARGET", "SUBSET_ONLY", "FULL_NO_SUBSET", "MULTI_KDMA", "MULTI_KDMA_SUBSET", "MULTI_KDMA_FULL_NO_SUBSET", "OPEN_WORLD"],
        'testing': True,
        'phase': 2
    },
    '2': {
        'cfgs': ["DEFAULT", "MULTI_KDMA"],
        'testing': False,
        'phase': 2
    },
    '3': {
        'cfgs': ["DEFAULT", "GROUP_TARGET"],
        'testing': True,
        'phase': 1
    }
}

"""
The below filepath definitions make simplifying assumptions and may need to be modified depending on the structure of your individual setup.
These modifications should be fairly trivial and targeted at the definition of CLIENT_ROOT and CLIENT_VENV_PYTHON.
However, if using a Unix-based machine such as a MacBook, further changes may be required. 
"""
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
#Assumes that the client repo is a folder with the same hierarchy as the server repo and is named itm-evaluation-client
CLIENT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIRECTORY, os.pardir, 'itm-evaluation-client'))
#Assumes that the client virtual environment is a folder with the same hierarchy as the server repo and is named evaluation_client
CLIENT_VENV_PYTHON = os.path.abspath(os.path.join(SCRIPT_DIRECTORY, os.pardir, 'evaluation_client', 'Scripts', 'python.exe'))
RUNNER_PATH = os.path.join(CLIENT_ROOT, 'itm_minimal_runner.py')

def wait_for_server_ui(port, timeout=30):
    url = f"http://localhost:{port}/ui/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200 and 'Swagger UI' in r.text:
                return
        except requests.RequestException:
            pass
        time.sleep(1.0)
    raise RuntimeError(f"Server UI did not become ready in {timeout}s")

def main():
    parser = argparse.ArgumentParser(description="Run integration ADM tests for ITM TA3 server.")
    parser.add_argument('--group', choices=GROUPS.keys(), required=True, help='Which test group to run.')
    parser.add_argument('--branch', required=True, help='Name of the branch under test, for output file naming.')
    parser.add_argument('--port', type=int, default=8080, help='Port the server listens on (default 8080).')
    args = parser.parse_args()

    group_info = GROUPS[args.group]
    for cfg in group_info['cfgs']:
        server_command = [sys.executable, '-m', 'swagger_server', '-c', cfg, '-p', str(args.port)]
        if group_info['testing']:
            server_command.append('-t')
        server = subprocess.Popen(server_command)
        try:
            wait_for_server_ui(args.port)
            outfile_name = f"{args.branch}_{cfg}_GROUP_{args.group}.txt"
            with open(outfile_name, 'w', encoding='utf-8') as f:
                runner_cmd = [CLIENT_VENV_PYTHON, RUNNER_PATH, '--name', 'integration_test', '--session', 'adept']
                if group_info['phase'] == 1:
                    runner_cmd.append('--domain')
                    runner_cmd.append('triage')
                subprocess.run(runner_cmd, cwd=CLIENT_ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)
        except Exception as e:
            logging.fatal(f"Error during run for config {cfg}: {e}")
        finally:
            logging.info("Stopping server.")
            server.terminate()
            server.wait(timeout=10)
            
main()