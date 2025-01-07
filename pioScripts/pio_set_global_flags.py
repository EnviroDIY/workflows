from os.path import join, realpath
from SCons.Script import BUILD_TARGETS  # pylint: disable=import-error
from SCons.Script import COMMAND_LINE_TARGETS  # pylint: disable=import-error
from SCons.Script import DEFAULT_TARGETS  # pylint: disable=import-error

Import("env")

if set(["_idedata", "idedata"]) & set(COMMAND_LINE_TARGETS):
    print("This is an IDE data build, exiting.")
    os._exit(os.EX_OK)

# append flags to local build environment (for just this library)
env.Append(
    CPPDEFINES=[
        ("NEOSWSERIAL_EXTERNAL_PCINT",),
        ("SDI12_EXTERNAL_PCINT",)
    ]
)
# print ">>>>>LOCAL ENV<<<<<"
# print env.Dump()

# append the same flags to the global build environment (for all libraries, etc)
global_env = DefaultEnvironment()
global_env.Append(
    CPPDEFINES=[
        ("NEOSWSERIAL_EXTERNAL_PCINT",),
        ("SDI12_EXTERNAL_PCINT",)
        ("MQTT_MAX_PACKET_SIZE",240)
    ]
)
# print "<<<<<GLOBAL ENV>>>>>"
# print global_env.Dump()
