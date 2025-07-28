import re
import fnmatch

def generate_list(input_list) -> list[str]:
    return [s.strip() for s in input_list.replace('\n', '').split(',') if s.strip()]

def load_filenames(token_string, scenario_files) -> list[str]:
    to_return = set()
    tokens = generate_list(token_string)
    for token in tokens:
        matches = set()
        if token in scenario_files:
            matches.add(token)
        else:
            matches.update(file for file in scenario_files if fnmatch.fnmatch(file, token))
            if len(matches) == 0:
                try:
                    pattern = token
                    if not (pattern.startswith('^') and pattern.endswith('$')):
                        pattern = f'^{pattern}$'
                    tokenRegex = re.compile(pattern)
                    matches.update(file for file in scenario_files if tokenRegex.match(file))
                except re.error:
                    pass
        to_return.update(matches)
    return sorted(to_return)