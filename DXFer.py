"""
DXFer, a Fusion 360 add-in
================================
DXFer is a Fusion 360 add-in for the bulk export of DXF Files.

:copyright: (c) 2020 by Patrick Rainsberry.
:license: Apache 2.0, see LICENSE for more details.

DXFer leverages the ezdxf library.
Copyright (C) 2011-2020, Manfred Moitzi
License: MIT License


Notice:
-------

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
import adsk.core
import traceback
from . import config
from . import utils

try:
    utils.check_apper(True)
    from .apper import apper

    # Import my commands
    from .commands.DXFerCommands import DXFExportCommand, PDFExportCommand

    # Create our addin definition object
    my_addin = apper.FusionApp(config.app_name, config.company_name, False)
    my_addin.root_path = config.app_path

    my_addin.add_command(
        'DXF Export',
        DXFExportCommand,
        {
            'cmd_description': 'DXF Export of Multiple Faces',
            'cmd_id': 'dxf_export_cmd',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'DXF Export',
            'toolbar_tab_name': 'TOOLS',
            'toolbar_tab_id': 'ToolsTab',
            'cmd_resources': 'command_icons',
            'command_visible': True,
            'command_promoted': True,

        }
    )

    my_addin.add_command(
        'PDF Export',
        PDFExportCommand,
        {
            'cmd_description': 'PDF Export of Multiple Faces',
            'cmd_id': 'pdf_export_cmd',
            'workspace': 'FusionSolidEnvironment',
            'toolbar_panel_id': 'DXF Export',
            'toolbar_tab_name': 'TOOLS',
            'toolbar_tab_id': 'ToolsTab',
            'cmd_resources': 'command_icons',
            'command_visible': True,
            'command_promoted': True,

        }
    )

except Exception as e:
    app = adsk.core.Application.get()
    ui = app.userInterface
    if ui:
        ui.messageBox('Initialization: {}'.format(traceback.format_exc()))

# Set to True to display various useful messages when debugging your app
debug = False

def run(context):
    my_addin.run_app()


def stop(context):
    my_addin.stop_app()

