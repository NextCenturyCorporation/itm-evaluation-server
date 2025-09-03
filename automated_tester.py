"""
Integration testing harness that automates dummy ADM runs.

Usage:
  python run_integration_tests.py --group <group_number> --branch <branch_name> [--port <port>]
  python run_integration_tests.py --validate-only

Existing Groups:
  Group 1: Phase 2 testing mode  - cfgs: DEFAULT, GROUP_TARGET, SUBSET_ONLY, FULL_NO_SUBSET, MULTI_KDMA, MULTI_KDMA_SUBSET, MULTI_KDMA_FULL_NO_SUBSET, OPEN_WORLD
  Group 2: Phase 2 normal mode   - cfgs: DEFAULT, MULTI_KDMA
  Group 3: Phase 1 testing mode  - cfgs: DEFAULT, GROUP_TARGET

Modifying groups:
  Edit the GROUPS object below. Each group must define:
    - cfgs:  list[str], non-empty; each must match a section in swagger_server/config.ini
    - testing: bool
    - phase: int in {1, 2}
  Unknown keys in a group are treated as errors by the validator.

Validation:
  Use --validate-only to validate GROUPS against swagger_server/config.ini and exit.
"""

import argparse
import subprocess
import time
import requests
import os
import sys
import logging
from configparser import ConfigParser

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

VALID_GROUP_KEYS = {"cfgs", "testing", "phase"}

def load_config_sections(config_path):
    final_path = os.path.abspath(os.path.expanduser(config_path))
    try:
        from swagger_server.config_util import read_ini
        parser, final_path_from_util = read_ini(final_path)
        final_path = final_path_from_util
    except Exception:
        if not os.path.exists(final_path):
            raise FileNotFoundError(f"Couldn't find file: {final_path}")
        parser = ConfigParser(os.environ)
        parser.read(final_path)
    sections = set(parser.sections())
    sections.add("DEFAULT")
    return sections, final_path

def validate_groups(groups, valid_cfg_names):
    errors = []
    if not isinstance(groups, dict) or not groups:
        return ["GROUPS must be a non-empty dictionary."]

    for name, definition in groups.items():
        if not isinstance(name, str) or not name.strip():
            errors.append(f"Group name {name} must be a non-empty string.")
        if not isinstance(definition, dict):
            errors.append(f"Group {name} value must be a dictionary.")
            continue

        keys = set(definition.keys())
        missing = VALID_GROUP_KEYS - keys
        extra = keys - VALID_GROUP_KEYS
        if missing:
            errors.append(f"Group {name}: missing required keys {missing}.")
        if extra:
            errors.append(f"Group {name}: unknown keys {extra}.")

        if missing:
            continue

        cfgs = definition.get("cfgs")
        if not isinstance(cfgs, (list, tuple)):
            errors.append(f"Group {name}: 'cfgs' must be a list of strings.")
        else:
            if len(cfgs) == 0:
                errors.append(f"Group {name}: 'cfgs' cannot be empty.")
            seen = set()
            for idx, cfg in enumerate(cfgs):
                if not isinstance(cfg, str) or not cfg.strip():
                    errors.append(f"Group {name}: cfgs[{idx}] must be a non-empty string.")
                    continue
                if cfg in seen:
                    errors.append(f"Group {name}: duplicate cfg '{cfg}'.")
                else:
                    seen.add(cfg)
                if cfg not in valid_cfg_names:
                    errors.append(f"Group {name}: cfg '{cfg}' not found in config.ini sections.")

        testing = definition.get("testing")
        if not isinstance(testing, bool):
            errors.append(f"Group {name}: 'testing' must be a boolean.")

        phase = definition.get("phase")
        if not isinstance(phase, int):
            errors.append(f"Group {name}: 'phase' must be an integer 1 or 2.")
        else:
            if phase not in (1, 2):
                errors.append(f"Group {name}: 'phase' must be 1 or 2, got {phase}.")
    
    return errors

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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Run integration ADM tests for ITM TA3 server.")
    parser.add_argument('--group', choices=GROUPS.keys(), required=False, help='Which test group to run (required unless --validate-only).')
    parser.add_argument('--branch', required=False, help='Name of the branch under test, for output file naming (required unless --validate-only).')
    parser.add_argument('--port', type=int, default=8080, help='Port the server listens on (default 8080).')
    parser.add_argument('--validate-only', action='store_true', help='Validate GROUPS against swagger_server/config.ini and exit.')
    args = parser.parse_args()

    if not args.validate_only:
        missing = []
        if args.group is None:
            missing.append('--group')
        if args.branch is None:
            missing.append('--branch')
        if missing:
            parser.error(f"The following arguments are required: {', '.join(missing)}")

    config_path = os.path.join(SCRIPT_DIRECTORY, 'swagger_server', 'config.ini')
    try:
        valid_cfgs, resolved_config_path = load_config_sections(config_path)
    except Exception as e:
        logging.fatal(f"Failed to read config sections from {config_path}.")
        sys.exit(1)

    errors = validate_groups(GROUPS, valid_cfgs)
    if args.validate_only:
        if errors:
            print("Validation Failed:")
            for counter, message in enumerate(errors, 1):
                print(f"  {counter:02d}. {message}")
            print(f"Checked against: {resolved_config_path}")
            sys.exit(1)
        else:
            print("Validation Passed.")
            print(f"Groups validated: {len(GROUPS)}")
            print(f"Checked against: {resolved_config_path}")
            sys.exit(0)

    if errors:
        logging.fatal("GROUPS validation failed. Run with --validate-only for details.")
        sys.exit(1)

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