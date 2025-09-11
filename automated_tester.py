"""
Integration testing harness that automates dummy ADM runs and pipes the output to an outfile.

Purposes
--------------------
• Validates the GROUPS dictionary against the active INI (swagger_server/config.ini). Section names (including DEFAULT) must
  match the cfgs listed in each group.
• For a selected group, starts the server per cfg (testing or normal mode), validates/chooses a port, waits for readiness,
  then starts to run the dummy ADM.
• Writes each runner's combined stdout/stderr to a text file for potential manual review.

Usage
--------------------
  python automated_tester.py --group <group_number> --branch <branch_name> [--port <port>] [--auto-port] [--client-root PATH] [--client-python PATH] [--runner-path PATH]
  python automated_tester.py --validate-only

Current Groups
--------------------
  Group 1: Phase 2 testing mode - cfgs: DEFAULT, GROUP_TARGET, SUBSET_ONLY, FULL_NO_SUBSET, MULTI_KDMA, MULTI_KDMA_SUBSET, MULTI_KDMA_FULL_NO_SUBSET, OPEN_WORLD
  Group 2: Phase 2 normal mode  - cfgs: DEFAULT, MULTI_KDMA
  Group 3: Phase 1 testing mode - cfgs: DEFAULT, GROUP_TARGET

Modifying Groups
--------------------
Edit the GROUPS object below. Each group must define:
  • cfgs:    list[str], non-empty; each value must match a section in swagger_server/config.ini (DEFAULT allowed)
  • testing: bool
  • phase:   int in {1, 2}

CLI Flags
--------------------
--group {…}:          Which test group to run (required unless --validate-only)
--branch NAME:        Branch label used in output filenames (required unless --validate-only)
--port N:             Port the server should use (default 8080; must be 1-65535 and available)
--auto-port:          Ask the OS for a free port; overrides --port
--client-root PATH:   Path to the evaluation client repo (absolute and relative paths both supported)
--client-python PATH: Path to the client venv Python (absolute and relative paths both supported)
--runner-path PATH:   Path to the runner script (absolute and relative paths both supported; defaults to <client_root>/itm_minimal_runner.py)
--validate-only:      Validate GROUPS against swagger_server/config.ini and exit (no path/port checks or execution)
"""

import argparse
import subprocess
import time
import requests
import os
import sys
import logging
import socket
import json
from pathlib import Path
from configparser import ConfigParser

GROUPS = {
    '1': {
        'cfgs': ["DEFAULT", "SUBSET_ONLY", "FULL_NO_SUBSET", "MULTI_KDMA", "MULTI_KDMA_SUBSET", "MULTI_KDMA_FULL_NO_SUBSET", "OPEN_WORLD"],
        'testing': True,
        'phase': 2
    },
    '2': {
        'cfgs': ["DEFAULT", "MULTI_KDMA"],
        'testing': False,
        'phase': 2
    },
    '3': {
        'cfgs': ["DEFAULT"],
        'testing': True,
        'phase': 1
    }
}

REPO_ROOT = Path(__file__).resolve().parent
TESTER_JSON_NAME = "automated_testing_paths.json"

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

def host_to_url(host, port, path= "/ui/"):
    if ":" in host:
        return f"http://[{host}]:{port}{path}"
    return f"http://{host}:{port}{path}"

def wait_for_server_ui(port, timeout=30):
    hosts = ["127.0.0.1", "::1", "localhost"]
    deadline = time.time() + timeout
    while time.time() < deadline:
        for host in hosts:
            try:
                url = host_to_url(host, port, "/ui/")
                r = requests.get(url, timeout=1)
                if r.status_code == 200 and 'Swagger UI' in r.text:
                    return
            except requests.RequestException:
                pass
        time.sleep(1.0)
    raise RuntimeError(f"Server UI did not become ready in {timeout}s")

def port_in_range(port):
    return isinstance(port, int) and 1 <= port <= 65535

def can_connect(host, port, timeout = 0.25):
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False

def is_port_free(port):
    for host in ("127.0.0.1", "::1"):
        if can_connect(host, port):
            return False
    return True

def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    if is_port_free(port):
        return port
    raise RuntimeError("Unable to find a free local port after multiple attempts.")

def resolve_port(requested_port, auto_port):
    if auto_port:
        return pick_free_port()
    if not port_in_range(requested_port):
        raise ValueError(f"Port {requested_port} is out of range (1-65535).")
    if not is_port_free(requested_port):
        raise RuntimeError(f"Port {requested_port} is already in use. Specify a different --port or use --auto-port.")
    return requested_port

def wait_for_port_free(port, timeout = 5.0, interval = 0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_port_free(port):
            return True
        time.sleep(interval)
    return False

def ensure_server_stopped(proc, port, auto_port):
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        logging.warning("Server did not terminate in time.")
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception as e:
           logging.warning(f"Failed to kill process cleanly: {e}.")

    if wait_for_port_free(port, timeout=5.0, interval=0.25):
        return port

    if auto_port:
        new_port = pick_free_port()
        return new_port
    else:
        logging.fatal(f"Port {port} remained busy after server stop. Rerun with --auto-port or specify a different --port.")
        sys.exit(1)

def resolve_user_path(potential_path, base):
    if not potential_path:
        return None
    p = Path(potential_path)
    return (p if p.is_absolute() else (base / p)).resolve()

def load_tester_json(config_dir):
    cfg_path = (config_dir / TESTER_JSON_NAME)
    if not cfg_path.exists():
        return {}
    try:
        with cfg_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
            if not isinstance(data, dict):
                logging.warning(f"{cfg_path} does not contain a JSON object.")
                return {}
            return data
    except Exception as e:
        logging.warning(f"Failed to read {cfg_path}: {e}.")
        return {}

def is_executable_file(potential_file):
    try:
        return potential_file.is_file() and os.access(str(potential_file), os.X_OK)
    except Exception:
        return False

def resolve_and_validate_paths(args):
    cfg = load_tester_json(REPO_ROOT)

    cli_client_root = resolve_user_path(getattr(args, "client_root", None), REPO_ROOT)
    json_client_root = resolve_user_path(cfg.get("client_root"), REPO_ROOT) if cfg else None
    client_root = None
    errors = []

    if cli_client_root and cli_client_root.is_dir():
        client_root = cli_client_root
    elif cli_client_root:
        logging.warning(f"Invalid Client Root From CLI: {cli_client_root}.")
        if json_client_root and json_client_root.is_dir():
            client_root = json_client_root
        else:
            errors.append(f"Client Root Not Found: {cli_client_root}.")
    else:
        if json_client_root and json_client_root.is_dir():
            client_root = json_client_root
        else:
            errors.append("Client Root Is Required (set via --client-root or automated_testing_paths.json).")

    cli_client_py = resolve_user_path(getattr(args, "client_python", None), REPO_ROOT)
    json_client_py = resolve_user_path(cfg.get("client_python"), REPO_ROOT) if cfg else None
    client_python = None

    if cli_client_py and is_executable_file(cli_client_py):
        client_python = cli_client_py
    elif cli_client_py:
        logging.warning(f"Invalid Client Python From CLI: {cli_client_py}.")
        if json_client_py and is_executable_file(json_client_py):
            client_python = json_client_py
        else:
            errors.append(f"Client Python Is Not Executable: {cli_client_py}")
    else:
        if json_client_py and is_executable_file(json_client_py):
            client_python = json_client_py
        else:
            errors.append("Client Python Is Required (set via --client-python or automated_testing_paths.json).")

    cli_runner = resolve_user_path(getattr(args, "runner_path", None), REPO_ROOT)
    json_runner = resolve_user_path(cfg.get("runner_path"), REPO_ROOT) if cfg else None
    
    if cli_runner and cli_runner.is_file():
        runner_path = cli_runner
    elif cli_runner:
        logging.warning(f"Invalid Runner Path From CLI (File Not Found): {cli_runner}.")
        if json_runner and json_runner.is_file():
            runner_path = json_runner
        else:
            runner_path = (client_root / "itm_minimal_runner.py") if client_root else None
    else:
        if json_runner and json_runner.is_file():
            runner_path = json_runner
        else:
            runner_path = (client_root / "itm_minimal_runner.py") if client_root else None

    if runner_path is None or not runner_path.is_file():
        errors.append("Runner Path Is Required (set via --runner-path or automated_testing_paths.json).")

    if errors:
        logging.error("Path Resolution Failed:")
        for counter, message in enumerate(errors, 1):
                print(f"  {counter:02d}. {message}")
        sys.exit(1)

    return client_root, client_python, runner_path

def main():
    parser = argparse.ArgumentParser(description="Run integration ADM tests for ITM TA3 server.")
    parser.add_argument('--group', choices=GROUPS.keys(), required=False, help='Which test group to run (required unless --validate-only).')
    parser.add_argument('--branch', required=False, help='Name of the branch under test, for output file naming (required unless --validate-only).')
    parser.add_argument('--port', type=int, default=8080, help='Port the server listens on (default 8080).')
    parser.add_argument('--auto-port', action='store_true', help='Pick a free local port automatically (overrides --port).')
    parser.add_argument('--client-root', dest='client_root', help='Path to the evaluation client repo.')
    parser.add_argument('--client-python', dest='client_python', help='Path to the client venv Python.')
    parser.add_argument('--runner-path', dest='runner_path', help='Path to the runner script.')
    parser.add_argument('--validate-only', action='store_true', help='Validate GROUPS against swagger_server/config.ini and exit.')
    args = parser.parse_args()

    port = None

    if not args.validate_only:
        missing = []
        if args.group is None:
            missing.append('--group')
        if args.branch is None:
            missing.append('--branch')
        if missing:
            parser.error(f"The following arguments are required: {', '.join(missing)}")
        try:
            port = resolve_port(args.port, args.auto_port)
        except Exception as e:
            logging.fatal(f"Port selection error: {e}.")
            sys.exit(1)
    
    if not args.validate_only:
        CLIENT_ROOT, CLIENT_VENV_PYTHON, RUNNER_PATH = resolve_and_validate_paths(args)

    config_path = os.path.join(REPO_ROOT, 'swagger_server', 'config.ini')
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
        if not is_port_free(port):
            logging.info(f"Port {port} busy before launching cfg '{cfg}'; Waiting for release.")
            if not wait_for_port_free(port, timeout=5.0, interval=0.25):
                if args.auto_port:
                    logging.info(f"Port {port} still busy; picking a new free port.")
                    port = pick_free_port()
                    logging.info(f"Switched to port {port}.")
                else:
                    logging.fatal(f"Port {port} became busy. Use a different --port or --auto-port.")
                    sys.exit(1)
        server_command = [sys.executable, '-m', 'swagger_server', '-c', cfg, '-p', str(port)]
        if group_info['testing']:
            server_command.append('-t')
        server = subprocess.Popen(server_command)
        try:
            wait_for_server_ui(port)
            outfile_name = f"{args.branch}_{cfg}_GROUP_{args.group}.txt"
            with open(outfile_name, 'w', encoding='utf-8') as f:
                runner_cmd = [str(CLIENT_VENV_PYTHON), str(RUNNER_PATH), '--name', 'integration_test', '--session', 'adept']
                if group_info['phase'] == 1:
                    runner_cmd.append('--domain')
                    runner_cmd.append('triage')
                env = os.environ.copy()
                env["TA3_HOSTNAME"] = "127.0.0.1"
                env["TA3_PORT"] = str(port)
                subprocess.run(runner_cmd, cwd=str(CLIENT_ROOT), stdout=f, stderr=subprocess.STDOUT, check=True, env=env)
        except Exception as e:
            logging.fatal(f"Error during run for config {cfg}: {e}")
        finally:
            logging.info("Stopping server.")
            port = ensure_server_stopped(server, port, args.auto_port)
            
main()
