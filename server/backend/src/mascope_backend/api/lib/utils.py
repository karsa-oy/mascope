import re


def generate_copy_name(original_name):
    if not original_name:
        return None

    # Clean the name by collapsing multiple spaces into one and trimming
    cleaned_name = " ".join(original_name.split()).strip()

    # Match the pattern for names like 'name Copy(1)', 'name Copy', etc.
    match = re.match(r"(.*\sCopy)(?:\((\d+)\))?$", cleaned_name)

    if match:
        base_name = match.group(1)
        copy_count = match.group(2)

        if copy_count:
            return f"{base_name}({int(copy_count) + 1})"
        else:
            return f"{base_name}(1)"
    else:
        return f"{cleaned_name} Copy"
