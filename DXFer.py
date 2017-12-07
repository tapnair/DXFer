# Author-Patrick Rainsberry
# Description-Calculates bolt holes

# Importing  Fusion Commands
# from .DXFerCommands import DXFImportCommand
from .DXFerCommands import DXFExportCommand


commands = []
command_definitions = []

# # Define parameters for 1st command
# cmd = {
#     'cmd_name': 'DXFer',
#     'cmd_description': 'DXF Stuff',
#     'cmd_id': 'cmdID_DXFHelper_1',
#     'cmd_resources': './resources',
#     'workspace': 'FusionSolidEnvironment',
#     'toolbar_panel_id': 'SolidScriptsAddinsPanel',
#     'class': DXFImportCommand
# }
# command_definitions.append(cmd)

# Define parameters for 1st command
cmd = {
    'cmd_name': 'DXFExportCommand',
    'cmd_description': 'DXF Export of Multiple Faces',
    'cmd_id': 'cmdID_DXFExportCommand',
    'cmd_resources': './resources',
    'workspace': 'FusionSolidEnvironment',
    'toolbar_panel_id': 'SolidScriptsAddinsPanel',
    'class': DXFExportCommand
}
command_definitions.append(cmd)

# Set to True to display various useful messages when debugging your app
debug = False

# Don't change anything below here:
for cmd_def in command_definitions:
    command = cmd_def['class'](cmd_def, debug)
    commands.append(command)


def run(context):
    for run_command in commands:
        run_command.on_run()


def stop(context):
    for stop_command in commands:
        stop_command.on_stop()