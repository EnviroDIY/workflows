#!/usr/bin/env python
"""
Shared utilities for matrix generation scripts and CI utilities.

Provides:
- Verbose output configuration
- Workspace and CI directory setup
- JSON file utilities
- Filename slug generation
- Matrix utilities (dict_product, deduplication)
"""

# %%
import os
import json
from itertools import product
from typing import List, Dict, Any

# %%
# Utilities for matrix generation and deduplication


# Source - https://stackoverflow.com/a/40623158
# Posted by Tarrasch, modified by community. See post 'Timeline' for change history
# Retrieved 2026-08-09, License - CC BY-SA 4.0
def dict_product(options):
    """
    >>> list(dict_product({'number': [1, 2], 'character': 'ab'}))
    [{'character': 'a', 'number': 1},
     {'character': 'a', 'number': 2},
     {'character': 'b', 'number': 1},
     {'character': 'b', 'number': 2}]
    """
    return (dict(zip(options.keys(), x)) for x in product(*options.values()))


def remove_nested_duplicates(list_with_dups):
    """Remove duplicates from a list of dictionaries or lists.

    Dictionaries are compared regardless of key ordering.
    Lists are compared regardless of item ordering, except for
    command-ordered fields (inline_defines, compiler_flags) which preserve order.
    Nested dictionaries and lists are handled recursively.

    For dictionaries, the 'job_group' key is ignored when comparing.
    """
    # Fields where list ordering indicates command order and must be preserved
    COMMAND_ORDERED_FIELDS = {"inline_defines", "compiler_flags"}

    def normalize(value, ignore_job_group=False, parent_key=None):
        """Recursively normalize a value for order-independent comparison.

        Args:
            value: The value to normalize
            ignore_job_group: Whether to ignore the 'job_group' key
            parent_key: The parent dictionary key containing this value
        """

        if isinstance(value, dict):
            return {
                k: normalize(v, parent_key=k)
                for k, v in value.items()
                if not (ignore_job_group and k == "job_group")
            }

        if isinstance(value, list):
            normalized_items = [
                normalize(item, parent_key=parent_key) for item in value
            ]

            # Preserve order for command-ordered fields; sort order-independent lists
            if parent_key in COMMAND_ORDERED_FIELDS:
                return normalized_items
            else:
                # Sort recursively normalized list items so list ordering
                # does not affect comparison for truly order-independent lists.
                return sorted(
                    normalized_items, key=lambda x: json.dumps(x, sort_keys=True)
                )

        return value

    seen = set()
    deduped_list = []

    for item in list_with_dups:

        # Only ignore job_group when the item itself is a dictionary.
        normalized_item = normalize(item, ignore_job_group=isinstance(item, dict))

        json_str = json.dumps(normalized_item, sort_keys=True)

        if json_str not in seen:
            seen.add(json_str)
            deduped_list.append(item)

    return deduped_list


# %%
# Utilities for loading and saving JSON files and generating filename-safe slugs
def load_json_file(filepath: str) -> Any:
    """Load a JSON file"""
    with open(filepath, "r") as f:
        return json.load(f)


def save_json_file(filepath: str, data: Any) -> None:
    """Save data to a JSON file"""
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def get_filename_slug(job_key, value) -> str:
    """Convert job values to filename-safe slugs"""
    replace_list = [
        ("BUILD_MODEM_", ""),
        ("BUILD_SENSOR_", ""),
        ("BUILD_PUB_", ""),
        ("BUILD_TEST_", ""),
        ("_PUBLISHER", ""),
        ("TINY_GSM_MODEM_", ""),
        ("_", "-"),
        (" ", "-"),
    ]

    def replace_all(s):
        for old, new in replace_list:
            s = s.replace(old, new)
        return s

    if job_key in ["compiler", "flag"]:
        return replace_all(value)
    elif job_key in ["board"]:
        if ":" in value:
            return replace_all(value.rsplit(":")[-1])
        else:
            return replace_all(value)
    elif (
        job_key in ["inline_defines", "compiler_flags"]
        and isinstance(value, list)
        and len(value) > 0
        and isinstance(value[0], list)
    ):
        return "-".join(
            [
                replace_all(f)
                for f in [
                    "-".join([replace_all(g) for g in sublist]) for sublist in value
                ]
            ]
        )
    elif job_key in ["inline_defines", "compiler_flags"] and isinstance(value, list):
        return "-".join([replace_all(f) for f in value])
    elif job_key in ["inline_defines", "compiler_flags"] and isinstance(value, str):
        return replace_all(value)
    elif job_key == "example":
        return replace_all(str(value).rsplit(os.path.sep)[-1])
    else:
        return replace_all(str(value))


# %%
# Platform and board configuration utilities dups
