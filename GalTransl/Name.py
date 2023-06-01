from typing import Dict
import csv


def load_name_table(name_table_path: str) -> Dict[str, str]:
    """
    This function loads the name table from the given path.

    Args:
    - name_table_path: The path to the name table.

    Returns:
    - A dictionary containing the name table.
    """
    name_table: Dict[str, str] = {}
    with open(name_table_path, mode="r", encoding="utf8") as f:
        reader = csv.reader(f)
        # Skip the header
        next(reader)
        for row in reader:
            name_table[row[0]] = row[1]
    return name_table
