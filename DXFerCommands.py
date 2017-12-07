import adsk.core
import adsk.fusion
import traceback

import sys
import os

from .Fusion360Utilities.Fusion360Utilities import get_app_objects
from .Fusion360Utilities.Fusion360CommandBase import Fusion360CommandBase

# Todo add and remove ass necessary only when making the call
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from .lib import ezdxf


# Get default directory
def get_default_app_dir():
    # Get user's home directory
    default_dir = os.path.expanduser("~")

    # Create a subdirectory for this application
    default_dir = os.path.join(default_dir, 'FusionDXFer', '')

    # Create the folder if it does not exist
    if not os.path.exists(default_dir):
        os.makedirs(default_dir)

    return default_dir


# def move_sketch(sketch):

    # #Working towards re-orient, but not working
    # b_box = sketch.boundingBox
    #
    # x = b_box.maxPoint.x - b_box.minPoint.x
    # y = b_box.maxPoint.y - b_box.minPoint.y
    #
    # transform_matrix = adsk.core.Matrix3D.create()
    # transform_matrix.translation = adsk.core.Vector3D.create(x, y, 0)
    # collection = adsk.core.ObjectCollection.create()
    #
    # for item in sketch.sketchCurves:
    #     collection.add(item)
    #
    # sketch.move(collection, transform_matrix)

class DXFImportCommand(Fusion360CommandBase):
    def on_execute(self, command, inputs, args, input_values):
        app_objects = get_app_objects()

        ui = app_objects['ui']

        file_name = os.path.join(os.path.dirname(__file__), 'test.dxf')

        dwg = ezdxf.readfile(file_name)

        ui.messageBox('opened   ' + dwg.dxfversion)

        blocks = dwg.blocks
        model_space = dwg.modelspace()

        for block in blocks:
            entities = block.query('*')
            for entity in entities:
                block.unlink_entity(entity)
                model_space.add_entity(entity)

    # The following is a basic sample of a dialog UI
    def on_create(self, command, command_inputs):

        # Gets necessary application objects
        app_objects = get_app_objects()
        default_units = app_objects['units_manager'].defaultLengthUnits


class DXFExportCommand(Fusion360CommandBase):

    def on_execute(self, command, inputs, args, input_values):

        app_objects = get_app_objects()
        ui = app_objects['ui']
        root_comp = app_objects['root_comp']
        sketches = root_comp.sketches

        file_name = input_values['file_name_input']

        target_drawing = ezdxf.new(dxfversion='AC1015')

        for i, face in enumerate(input_values['faces']):

            new_name = file_name + '_' + str(i)
            new_name = os.path.join(get_default_app_dir(), new_name)
            new_name += '.dxf'

            sketch = sketches.add(face)
            sketch.saveAsDXF(new_name)
            sketch.deleteMe()

            dwg = ezdxf.readfile(new_name)

            if input_values['dxf_option_group'] == 'Blocks':
                dwg.blocks.new('Face_' + str(i))
                block = dwg.blocks.get('Face_' + str(i))

                for entity in dwg.entities:
                    dwg.modelspace().unlink_entity(entity)
                    block.add_entity(entity)

            elif input_values['dxf_option_group'] == 'Layers':
                for entity in dwg.entities:
                    entity.dxf.layer = 'Face_' + str(i)

            importer = ezdxf.Importer(dwg, target_drawing)
            importer.import_modelspace_entities('*')
            os.remove(new_name)

        file_name += '.dxf'
        target_drawing.saveas(file_name)

        ui.messageBox('DXF File exported to: ' + file_name)

    # The following is a basic sample of a dialog UI
    def on_create(self, command: adsk.core.Command, command_inputs: adsk.core.CommandInputs):

        # Gets necessary application objects
        app_objects = get_app_objects()

        doc_name = app_objects['document'].name
        default_file_name = os.path.join(get_default_app_dir(), doc_name)
        command_inputs.addStringValueInput('file_name_input', 'File Name: ', default_file_name)

        selection_input = command_inputs.addSelectionInput('faces', 'Select Faces: ',
                                                           'Select faces to add to dxf output')
        selection_input.addSelectionFilter('PlanarFaces')
        selection_input.setSelectionLimits(1, 0)

        dxf_title = command_inputs.addTextBoxCommandInput('dxf_title', '',
                                                          '<b>How to seperate faces in new DXF?:</b>', 1, True)
        dxf_title.isVisible = True

        dxf_option_group = command_inputs.addRadioButtonGroupCommandInput('dxf_option_group')
        dxf_option_group.listItems.add('Blocks', True)
        dxf_option_group.listItems.add('Layers', False)
        dxf_option_group.listItems.add('Flat', False)
        dxf_option_group.isVisible = True

        dxf_warning_text = '<br> <b>Note! </b><br><br>' \
                           'All faces will be moved to origin in output DXF<br><br>' \
                           '<i>Depending on orientation of the face results may be unpredictable</i>'

        dxf_warning_input = command_inputs.addTextBoxCommandInput('warning', '',
                                                                  dxf_warning_text, 16, True)
        dxf_warning_input.isVisible = True
