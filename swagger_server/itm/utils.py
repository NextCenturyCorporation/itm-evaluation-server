import re
import fnmatch

def generate_list(input_list) -> list[str]:
    return [s.strip() for s in input_list.replace('\n', '').split(',') if s.strip()]

def load_filenames(token_string, scenario_files) -> list[str]:
    to_return = set()
    tokens = generate_list(token_string)
    remaining = set(scenario_files)
    for token in tokens:
        matches = set()
        if token in remaining:
            matches.add(token)
        else:
            glob_matches = set(input_file for input_file in remaining if fnmatch.fnmatch(input_file, token))
            if len(glob_matches) > 0:
                matches.update(glob_matches)
            else:
                try:
                    pattern = token
                    if not (pattern.startswith('^') and pattern.endswith('$')):
                        pattern = f'^{pattern}$'
                    token_regex = re.compile(pattern)
                    matches.update(input_file for input_file in remaining if token_regex.match(input_file))
                except re.error:
                    pass

        to_return.update(matches)
        remaining.difference_update(matches)

        if len(remaining) == 0:
            break
    return sorted(to_return)
