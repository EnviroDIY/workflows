from SCons.Script import BUILD_TARGETS  # pylint: disable=import-error
from SCons.Script import COMMAND_LINE_TARGETS  # pylint: disable=import-error
from SCons.Script import DEFAULT_TARGETS  # pylint: disable=import-error

Import("env")

print("Running set_project_dirs.py on environment (PIOENV) {}".format(env["PIOENV"]))
print(f"Current build targets: {BUILD_TARGETS}")
print(f"Current command line targets: {COMMAND_LINE_TARGETS}")

if set(["_idedata", "idedata"]) & set(COMMAND_LINE_TARGETS):
    print("This is an IDE data build, exiting.")
    env.Exit(0)

# https://docs.platformio.org/en/latest/scripting/custom_targets.html

# Single action/command per 1 target
env.AddCustomTarget("sysenv", None, 'python -c "import os; print(os.environ)"')

# Multiple actions
env.AddCustomTarget(
    name="pioenv",
    dependencies=None,
    actions=["pio --version", "python --version"],
    title="Core Env",
    description="Show PlatformIO Core and Python versions",
)
