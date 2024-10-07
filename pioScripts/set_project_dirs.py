import os
import sys
import subprocess

from SCons.Script import BUILD_TARGETS  # pylint: disable=import-error
from SCons.Script import COMMAND_LINE_TARGETS  # pylint: disable=import-error
from SCons.Script import DEFAULT_TARGETS  # pylint: disable=import-error

Import("env")

print("Running set_project_dirs.py on environment (PIOENV) {}".format(env["PIOENV"]))
print(f"Current build targets: {[str(tgt) for tgt in BUILD_TARGETS]}")
print(f"Current command line targets: {COMMAND_LINE_TARGETS}")
print(f"Is a clean: {env.IsCleanTarget()}")
print(
    f"Is an IDE build: {len(set(['_idedata', 'idedata']) & set(COMMAND_LINE_TARGETS))!=0}"
)

# if set(["_idedata", "idedata"]) & set(COMMAND_LINE_TARGETS):
#     print("This is an IDE data build, exiting.")
#     env.Exit(0)

# include toolchain paths
env.Replace(COMPILATIONDB_INCLUDE_TOOLCHAIN=True)
dump_dir = f"{env['PROJECT_WORKSPACE_DIR']}\\config\\{env['PIOENV']}"

if not os.path.exists(dump_dir):
    os.makedirs(dump_dir)

# override compilation DB path
if env["PIOENV"] in ["compile_db", "working"]:
    print(
        f"Setting compile command output to {os.path.join('$PROJECT_DIR/.vscode', 'compile_commands.json')}"
    )
    env.Replace(
        COMPILATIONDB_PATH=os.path.join("$PROJECT_DIR/.vscode", "compile_commands.json")
    )
else:
    print(
        f"Setting compile command output to {os.path.join(dump_dir, 'compile_commands.json')}"
    )
    env.Replace(COMPILATIONDB_PATH=os.path.join(dump_dir, "compile_commands.json"))
