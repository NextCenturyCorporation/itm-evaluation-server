import re
import fnmatch

def generate_list(input_list) -> list[str]:
    return [s.strip() for s in input_list.replace('\n', '').split(',') if s.strip()]

def resolve_tokens(token_string, universe) -> list[str]:
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

    return sorted(matched)
