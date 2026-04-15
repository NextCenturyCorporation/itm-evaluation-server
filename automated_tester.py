"""
Integration testing harness that automates dummy ADM runs and pipes the output to outfiles.

Purposes
--------------------
• Validates the resolved test groups against the active INI (swagger_server/config.ini). Section names (including DEFAULT)
  must match the cfgs listed in each group.
• For a selected group, starts the server per cfg (testing or normal mode), validates or chooses a port, waits for
  readiness, then runs the dummy ADM.
• Writes each runner's combined stdout and stderr to branch-scoped text files for potential manual review.

Usage
--------------------
  python3 automated_tester.py --group <group_number> --branch <branch_name> [--port <port>] [--auto-port] [--client-root PATH] [--client-python PATH] [--runner-path PATH]
  python3 automated_tester.py --validate-only

Default Groups
--------------------
  Group 1: Phase 2 testing mode - cfgs: DEFAULT, FEB_OPENWORLD, JUNE_OPENWORLD
  Group 2: Phase 2 normal mode  - cfgs: DEFAULT, FEB_OPENWORLD, JUNE_OPENWORLD
  Group 3: Phase 1 testing mode - cfgs: DEFAULT

Local Config
--------------------
Copy automated_testing_config.template.json to automated_testing_config.json for local paths and optional local group
overrides. automated_testing_config.json is ignored by Git.

CLI Flags
--------------------
--group {…}:          Which test group to run (required unless --validate-only)
--branch NAME:        Branch label used in output directory naming (required unless --validate-only)
--port N:             Port the server should use (default 8080; must be 1-65535 and available)
--auto-port:          Ask the OS for a free port; overrides --port
--client-root PATH:   Path to the evaluation client repo (absolute and relative paths both supported)
--client-python PATH: Path to the client venv Python (absolute and relative paths both supported)
--runner-path PATH:   Path to the runner script (absolute and relative paths both supported; defaults to <client_root>/itm_minimal_runner.py)
--validate-only:      Validate resolved groups against swagger_server/config.ini and exit (no path or port checks or execution)
"""

import argparse
import copy
import json
import logging
import os
import fnmatch
import re
import socket
import subprocess
import sys
import time
from configparser import ConfigParser
from pathlib import Path
from urllib.parse import urlparse

import requests

DEFAULT_GROUPS = {
    '1': {
        'cfgs': ["DEFAULT", "FEB_OPENWORLD", "JUNE_OPENWORLD"],
        'testing': True,
        'phase': 2
    },
    '2': {
        'cfgs': ["DEFAULT"],
        'testing': False,
        'phase': 2
    },
    '3': {
        'cfgs': ["DEFAULT"],
        'testing': True,
        'phase': 1
    }
}

DEFAULT_TESTER_CONFIG = {
    'client_root': None,
    'client_python': None,
    'runner_path': None,
    'groups': {}
}

REPO_ROOT = Path(__file__).resolve().parent
TESTER_CONFIG_NAME = "automated_testing_config.json"
TESTER_CONFIG_TEMPLATE_NAME = "automated_testing_config.template.json"
RESULTS_ROOT = REPO_ROOT / "automated_test_results"

VALID_GROUP_KEYS = {"cfgs", "testing", "phase"}

def generate_list(input_list):
    return [s.strip() for s in input_list.replace('\n', '').split(',') if s.strip()]

def resolve_tokens(token_string, universe):
    matched = set()
    tokens = generate_list(token_string)
    remaining = set(universe)
    for token in tokens:
        current_matches = set()
        if token in remaining:
            current_matches.add(token)
        else:
            glob_matches = {entry for entry in remaining if fnmatch.fnmatch(entry, token)}
            if len(glob_matches) > 0:
                current_matches.update(glob_matches)
            else:
                try:
                    pattern = token
                    if not (pattern.startswith('^') and pattern.endswith('$')):
                        pattern = f'^{pattern}$'
                    token_regex = re.compile(pattern)
                    current_matches.update(entry for entry in remaining if token_regex.match(entry))
                except re.error:
                    pass

        matched.update(current_matches)
        remaining.difference_update(current_matches)

        if len(remaining) == 0:
            break

    return matched

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

def load_runtime_config(config_path):
    final_path = os.path.abspath(os.path.expanduser(config_path))
    if not os.path.exists(final_path):
        raise FileNotFoundError(f"Couldn't find file: {final_path}")
    parser = ConfigParser(os.environ)
    parser.read(final_path)
    return parser, final_path

def resolve_scenario_directory(config_section):
    scenario_directory = config_section.get('SCENARIO_DIRECTORY')
    scenario_path = resolve_user_path(scenario_directory, REPO_ROOT)
    if scenario_path is None or not scenario_path.is_dir():
        raise RuntimeError("Invalid filepath. Please check the SCENARIO_DIRECTORY variable in the config.ini file.")
    return scenario_path

def validate_eval_filenames(config_section, scenario_path, cfg_name):
    eval_filenames = config_section.get('ADEPT_EVAL_FILENAMES')
    if eval_filenames is None:
        raise RuntimeError(f"Config '{cfg_name}' is missing ADEPT_EVAL_FILENAMES.")

    scenario_files = set(os.listdir(scenario_path))
    if len(scenario_files) == 0:
        raise RuntimeError(f"Scenario directory '{scenario_path}' is empty for config '{cfg_name}'.")

    missing_tokens = []
    for token in generate_list(eval_filenames):
        if len(resolve_tokens(token, scenario_files)) == 0:
            missing_tokens.append(token)

    if missing_tokens:
        joined_tokens = ", ".join(missing_tokens)
        raise RuntimeError(
            f"Config '{cfg_name}' references scenario file patterns that did not match any local files in "
            f"'{scenario_path}': {joined_tokens}"
        )

def preflight_cfg_run(config_path, cfg_name):
    parser, _ = load_runtime_config(config_path)
    if cfg_name != 'DEFAULT' and cfg_name not in parser:
        raise RuntimeError(f"Config group '{cfg_name}' does not exist in {config_path}.")
    config_section = parser[cfg_name]
    scenario_path = resolve_scenario_directory(config_section)
    validate_eval_filenames(config_section, scenario_path, cfg_name)

def validate_ta1_connectivity(config_section, cfg_name):
    ta1_names = generate_list(config_section.get('ALL_TA1_NAMES', ''))
    for ta1_name in ta1_names:
        ta1_url = config_section.get(f"{ta1_name.upper()}_URL")
        if ta1_url is None or ta1_url.strip() == "":
            raise RuntimeError(f"Config '{cfg_name}' is missing {ta1_name.upper()}_URL.")
        parsed = urlparse(ta1_url if "://" in ta1_url else f"http://{ta1_url}")
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if host is None:
            raise RuntimeError(f"Config '{cfg_name}' contains an invalid URL for {ta1_name.upper()}_URL: {ta1_url}")
        if not can_connect(host, port, timeout=5):
            raise RuntimeError(f"Could not connect to configured TA1 '{ta1_name}' at {ta1_url}.")

def ensure_runner_exercised_scenarios(output_path, cfg_name):
    output_text = output_path.read_text(encoding='utf-8')
    if "Scenario name:" in output_text:
        return
    if "Session " in output_text and " complete" in output_text:
        raise RuntimeError(
            f"Runner completed for config '{cfg_name}' without exercising any scenarios. "
            "Check the config group and local scenario data."
        )
    raise RuntimeError(f"Runner produced no scenario output for config '{cfg_name}'.")

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
        elif phase not in (1, 2):
            errors.append(f"Group {name}: 'phase' must be 1 or 2, got {phase}.")

    return errors

def host_to_url(host, port, path="/ui/"):
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
                response = requests.get(url, timeout=1)
                if response.status_code == 200 and 'Swagger UI' in response.text:
                    return
            except requests.RequestException:
                pass
        time.sleep(1.0)
    raise RuntimeError(f"Server UI did not become ready in {timeout}s")

def port_in_range(port):
    return isinstance(port, int) and 1 <= port <= 65535

def can_connect(host, port, timeout=0.25):
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False

def is_port_free(port):
    for host in ("127.0.0.1", "::1"):
        if can_connect(host, port):
            return False
    return True

def pick_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
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

def wait_for_port_free(port, timeout=5.0, interval=0.25):
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
        return pick_free_port()

    logging.fatal(f"Port {port} remained busy after server stop. Rerun with --auto-port or specify a different --port.")
    sys.exit(1)

def resolve_user_path(potential_path, base):
    if not potential_path:
        return None
    potential = Path(potential_path)
    return (potential if potential.is_absolute() else (base / potential)).resolve()

def load_tester_json(config_dir):
    cfg_path = config_dir / TESTER_CONFIG_NAME
    if not cfg_path.exists():
        return {}, None
    try:
        with cfg_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as e:
        logging.warning(f"Failed to read {cfg_path}: {e}.")
        return {}, None

    if not isinstance(data, dict):
        logging.warning(f"{cfg_path} does not contain a JSON object.")
        return {}, None

    return data, cfg_path

def resolve_groups(config_groups):
    groups = copy.deepcopy(DEFAULT_GROUPS)
    if config_groups is None:
        return groups
    if not isinstance(config_groups, dict):
        raise ValueError("Configured groups must be a JSON object.")
    for name, definition in config_groups.items():
        groups[name] = definition
    return groups

def load_tester_config(config_dir):
    local_cfg, cfg_path = load_tester_json(config_dir)
    resolved_cfg = copy.deepcopy(DEFAULT_TESTER_CONFIG)
    for key in ('client_root', 'client_python', 'runner_path'):
        if key in local_cfg:
            resolved_cfg[key] = local_cfg[key]
    resolved_cfg['groups'] = resolve_groups(local_cfg.get('groups'))
    return resolved_cfg, cfg_path

def is_executable_file(potential_file):
    try:
        return potential_file.is_file() and os.access(str(potential_file), os.X_OK)
    except Exception:
        return False

def resolve_and_validate_paths(args, tester_cfg):
    cli_client_root = resolve_user_path(getattr(args, "client_root", None), REPO_ROOT)
    cfg_client_root = resolve_user_path(tester_cfg.get("client_root"), REPO_ROOT)
    client_root = None
    errors = []

    if cli_client_root and cli_client_root.is_dir():
        client_root = cli_client_root
    elif cli_client_root:
        logging.warning(f"Invalid Client Root From CLI: {cli_client_root}.")
        if cfg_client_root and cfg_client_root.is_dir():
            client_root = cfg_client_root
        else:
            errors.append(f"Client Root Not Found: {cli_client_root}.")
    else:
        if cfg_client_root and cfg_client_root.is_dir():
            client_root = cfg_client_root
        else:
            errors.append(f"Client Root Is Required (set via --client-root or {TESTER_CONFIG_NAME}).")

    cli_client_py = resolve_user_path(getattr(args, "client_python", None), REPO_ROOT)
    cfg_client_py = resolve_user_path(tester_cfg.get("client_python"), REPO_ROOT)
    client_python = None

    if cli_client_py and is_executable_file(cli_client_py):
        client_python = cli_client_py
    elif cli_client_py:
        logging.warning(f"Invalid Client Python From CLI: {cli_client_py}.")
        if cfg_client_py and is_executable_file(cfg_client_py):
            client_python = cfg_client_py
        else:
            errors.append(f"Client Python Is Not Executable: {cli_client_py}")
    else:
        if cfg_client_py and is_executable_file(cfg_client_py):
            client_python = cfg_client_py
        else:
            errors.append(f"Client Python Is Required (set via --client-python or {TESTER_CONFIG_NAME}).")

    cli_runner = resolve_user_path(getattr(args, "runner_path", None), REPO_ROOT)
    cfg_runner = resolve_user_path(tester_cfg.get("runner_path"), REPO_ROOT)
    runner_path = None

    if cli_runner and cli_runner.is_file():
        runner_path = cli_runner
    elif cli_runner:
        logging.warning(f"Invalid Runner Path From CLI (File Not Found): {cli_runner}.")
        if cfg_runner and cfg_runner.is_file():
            runner_path = cfg_runner
        else:
            runner_path = (client_root / "itm_minimal_runner.py") if client_root else None
    else:
        if cfg_runner and cfg_runner.is_file():
            runner_path = cfg_runner
        else:
            runner_path = (client_root / "itm_minimal_runner.py") if client_root else None

    if runner_path is None or not runner_path.is_file():
        errors.append(f"Runner Path Is Required (set via --runner-path or {TESTER_CONFIG_NAME}).")

    if errors:
        logging.error("Path Resolution Failed:")
        for counter, message in enumerate(errors, 1):
            print(f"  {counter:02d}. {message}")
        sys.exit(1)

    return client_root, client_python, runner_path

def sanitize_branch_name(branch_name):
    sanitized = re.sub(r'[\\/]+', '_', branch_name.strip())
    sanitized = re.sub(r'[^A-Za-z0-9._-]+', '_', sanitized)
    sanitized = sanitized.strip("._-")
    return sanitized if sanitized else "unnamed_branch"

def build_output_path(branch_name, cfg, group_name):
    branch_dir = RESULTS_ROOT / sanitize_branch_name(branch_name)
    branch_dir.mkdir(parents=True, exist_ok=True)
    return branch_dir / f"{cfg}_GROUP_{group_name}.txt"

def build_runner_command(client_venv_python, runner_path, phase):
    runner_cmd = [str(client_venv_python), str(runner_path), '--name', 'integration_test', '--session', 'adept']
    if phase == 1:
        runner_cmd.extend(['--domain', 'triage'])
    return runner_cmd

def parse_args():
    parser = argparse.ArgumentParser(description="Run integration ADM tests for ITM TA3 server.")
    parser.add_argument('--group', required=False, help='Which test group to run (required unless --validate-only).')
    parser.add_argument('--branch', required=False, help='Name of the branch under test, for output directory naming (required unless --validate-only).')
    parser.add_argument('--port', type=int, default=8080, help='Port the server listens on (default 8080).')
    parser.add_argument('--auto-port', action='store_true', help='Pick a free local port automatically (overrides --port).')
    parser.add_argument('--client-root', dest='client_root', help='Path to the evaluation client repo.')
    parser.add_argument('--client-python', dest='client_python', help='Path to the client venv Python.')
    parser.add_argument('--runner-path', dest='runner_path', help='Path to the runner script.')
    parser.add_argument('--validate-only', action='store_true', help='Validate resolved groups against swagger_server/config.ini and exit.')
    return parser.parse_args()

def main():
    args = parse_args()
    try:
        tester_cfg, _ = load_tester_config(REPO_ROOT)
    except ValueError as e:
        logging.fatal(f"Tester configuration error: {e}.")
        sys.exit(1)
    groups = tester_cfg['groups']

    port = None

    if not args.validate_only:
        missing = []
        if args.group is None:
            missing.append('--group')
        if args.branch is None:
            missing.append('--branch')
        if missing:
            raise SystemExit(f"usage error: The following arguments are required: {', '.join(missing)}")
        if args.group not in groups:
            raise SystemExit(f"Unknown group '{args.group}'. Valid groups: {', '.join(sorted(groups.keys()))}")
        try:
            port = resolve_port(args.port, args.auto_port)
        except Exception as e:
            logging.fatal(f"Port selection error: {e}.")
            sys.exit(1)

    if not args.validate_only:
        client_root, client_venv_python, runner_path = resolve_and_validate_paths(args, tester_cfg)

    config_path = os.path.join(REPO_ROOT, 'swagger_server', 'config.ini')
    try:
        valid_cfgs, resolved_config_path = load_config_sections(config_path)
    except Exception:
        logging.fatal(f"Failed to read config sections from {config_path}.")
        sys.exit(1)

    errors = validate_groups(groups, valid_cfgs)
    if args.validate_only:
        if errors:
            print("Validation Failed:")
            for counter, message in enumerate(errors, 1):
                print(f"  {counter:02d}. {message}")
            print(f"Groups validated: {len(groups)}")
            print(f"Checked against: {resolved_config_path}")
            sys.exit(1)
        print("Validation Passed.")
        print(f"Groups validated: {len(groups)}")
        print(f"Checked against: {resolved_config_path}")
        sys.exit(0)

    if errors:
        logging.fatal("GROUPS validation failed. Run with --validate-only for details.")
        sys.exit(1)

    group_info = groups[args.group]
    for cfg in group_info['cfgs']:
        try:
            preflight_cfg_run(config_path, cfg)
            if not group_info['testing']:
                validate_ta1_connectivity(load_runtime_config(config_path)[0][cfg], cfg)
        except Exception as e:
            logging.fatal(f"Preflight failed for config {cfg}: {e}")
            sys.exit(1)
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
            output_path = build_output_path(args.branch, cfg, args.group)
            with output_path.open('w', encoding='utf-8') as fh:
                runner_cmd = build_runner_command(client_venv_python, runner_path, group_info['phase'])
                env = os.environ.copy()
                env["TA3_HOSTNAME"] = "127.0.0.1"
                env["TA3_PORT"] = str(port)
                subprocess.run(runner_cmd, cwd=str(client_root), stdout=fh, stderr=subprocess.STDOUT, check=True, env=env)
            ensure_runner_exercised_scenarios(output_path, cfg)
        except Exception as e:
            logging.fatal(f"Error during run for config {cfg}: {e}")
        finally:
            logging.info("Stopping server.")
            port = ensure_server_stopped(server, port, args.auto_port)

if __name__ == '__main__':
    main()
