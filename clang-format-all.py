# %%
import os
import subprocess
from pathlib import Path
import configargparse as argparse
import logging
from typing import List

# modified from https://github.com/thebigG/clang_format_all/blob/main/src/clang_format_all/clang_format_all.py

logging.basicConfig()
logger = logging.getLogger("check-all")
logger.setLevel(logging.INFO)

default_extensions = [
    ".cpp",
    ".cc",
    ".C",
    ".CPP",
    ".c++",
    ".cp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".H",
    ".tpp",
    ".ino",
]

default_exclusions = [
    ".history",
    ".git",
    ".github",
    ".pio",
    ".vscode",
    "archive",
    "build",
    "bin",
    "docs",
    "ci",
    "continuous_integration",
    "continuous_integration_artifacts",
    "lib",
    "include",
    "external",
    "third_party",
    "__pycache__",
]


# %%
def parse_input_args():
    parser = argparse.ArgumentParser(
        description="clang_format_all starts at this directory and drills down recursively"
    )

    parser.add_argument(
        "--root_dir",
        type=str,
        required=False,
        help="Root Directory",
        default=os.getcwd(),
    )

    parser.add_argument(
        "--file_extensions",
        type=str,
        required=False,
        nargs="+",
        help="File extensions to check or format",
        default=default_extensions,
    )

    parser.add_argument(
        "--exclude_dirs",
        type=str,
        required=False,
        nargs="+",
        help="Files/Folders to Exclude",
        default=default_exclusions,
    )
    parser.add_argument(
        "--exclude_files",
        type=str,
        required=False,
        nargs="+",
        help="Files to Exclude",
        default=[],
    )

    args, _ = parser.parse_known_args()
    parser.print_values()
    return args


def get_all_files(
    root_dir: str,
    file_extensions: set | None = None,
    exclude_dirs: set | None = None,
    exclude_files: set | None = None,
) -> List:
    if file_extensions is None:
        file_extensions = set(default_extensions)
    if exclude_dirs is None:
        exclude_dirs = set(default_exclusions)
    if exclude_files is None:
        exclude_files = set()

    files_array = []
    for root, dirs, files in os.walk(root_dir, topdown=True):
        dirs[:] = [
            d
            for d in dirs
            if d not in exclude_dirs and os.path.join(root, d) not in exclude_dirs
        ]
        for file in files:
            path = os.path.join(root, file)
            if file in exclude_files or path in exclude_files:
                continue
            if Path(path).suffix in file_extensions:
                files_array.append(path)
    return files_array


def find_clang_format_style_file(start_dir: str) -> str | None:
    current_dir = Path(start_dir).resolve()
    while True:
        style_file = current_dir / ".clang-format"
        if style_file.exists():
            return str(style_file)
        if current_dir.parent == current_dir:
            break
        current_dir = current_dir.parent
    return None


def format_all(file_list: List[str]):
    for path in file_list:
        style_file = find_clang_format_style_file(os.path.dirname(path))
        command_list = [
            "C:\\Program Files\\LLVM\\bin\\clang-format.exe",
            f"-style=file:{style_file}" if style_file else "-style=file",
            "-i",
            path,
        ]
        print(f"\tCalling clang-format: {subprocess.list2cmdline(command_list)}")
        if (
            subprocess.run(
                [
                    "C:\\Program Files\\LLVM\\bin\\clang-format.exe",
                    "-style=file",
                    "-i",
                    path,
                ],
                capture_output=True,
            ).returncode
            != 0
        ):
            logger.info('"%s": An error occurred while parsing this file.', path)
            exit(-1)
        else:
            logger.info('"%s": parsed successfully.', path)


def main():
    args = parse_input_args()
    root_dir = Path(args.root_dir).resolve()
    file_extensions = (
        set(args.file_extensions) if args.file_extensions else set(default_extensions)
    )
    exclude_dirs = (
        set(args.exclude_dirs) if args.exclude_dirs else set(default_exclusions)
    )
    exclude_files = set(args.exclude_files) if args.exclude_files else set()
    files_to_format = get_all_files(
        root_dir=str(root_dir),
        file_extensions=file_extensions,
        exclude_dirs=exclude_dirs,
        exclude_files=exclude_files,
    )
    format_all(files_to_format)


# %%
if __name__ == "__main__":
    main()

# cSpell:ignore topdown
