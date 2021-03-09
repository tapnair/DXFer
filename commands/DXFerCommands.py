import importlib
import sys

import adsk.core
import adsk.fusion
import traceback

import os

from ..apper import apper
from .. import config


def check_dependency(module_name: str, dependency_name: str):
    test_dir = os.path.join(config.lib_path, module_name)
    success = True
    if not os.path.exists(test_dir):
        success = apper.Fusion360PipInstaller.install_from_list([dependency_name], config.lib_path)

    if not success:
        raise ImportError(f'Unable to install module {module_name}')


@apper.lib_import(config.lib_path)
def add_to_dxf(file_name, dxf_option, target_drawing):
    check_dependency('ezdxf', 'ezdxf')
    import ezdxf
    from ezdxf.addons import Importer

    dwg = ezdxf.readfile(file_name)
    obj_name = file_name[file_name.rfind(os.path.pathsep):-4]
    if dxf_option == 'Blocks':
        dwg.blocks.new(obj_name)
        block = dwg.blocks.get(obj_name)

        for entity in dwg.entities:
            dwg.modelspace().unlink_entity(entity)
            block.add_entity(entity)

    elif dxf_option == 'Layers':
        for entity in dwg.entities:
            entity.dxf.layer = obj_name

    importer = Importer(dwg, target_drawing)
    importer.import_entities(dwg.entities)


@apper.lib_import(config.lib_path)
def create_empty_dxf():
    check_dependency('ezdxf', 'ezdxf')
    import ezdxf

    new_dwg = ezdxf.new(dxfversion='AC1015')
    return new_dwg


@apper.lib_import(config.lib_path)
def export_pdf(dxf_file):
    check_dependency('matplotlib', 'ezdxf[draw]')
    import ezdxf
    from ezdxf.addons.drawing import matplotlib

    dwg = ezdxf.readfile(dxf_file)
    pdf_file_name = f'{dxf_file[:-4]}.pdf'
    matplotlib.qsave(dwg.modelspace(), pdf_file_name)


def make_offset_sketch(face: adsk.fusion.BRepFace, offset: float):
    ao = apper.AppObjects()
    root_comp = ao.root_comp
    sketches = root_comp.sketches

    sketch = sketches.add(face)

    direction_point = face.pointOnFace

    loop_collections = []
    outer_profile: adsk.fusion.Profile = sketch.profiles.item(0)
    length = 0

    if sketch.profiles.count > 1:
        profile: adsk.fusion.Profile
        for profile in sketch.profiles:
            this_length = profile.boundingBox.minPoint.distanceTo(profile.boundingBox.maxPoint)
            if this_length > length:
                outer_profile = profile
                length = this_length

    loop: adsk.fusion.ProfileLoop
    for loop in outer_profile.profileLoops:
        loop_collection = adsk.core.ObjectCollection.create()
        profile_curve: adsk.fusion.ProfileCurve
        for profile_curve in loop.profileCurves:
            loop_collection.add(profile_curve.sketchEntity)
        loop_collections.append(loop_collection)

    loop_collection: adsk.core.ObjectCollection
    for loop_collection in loop_collections:
        sketch.offset(loop_collection, direction_point, offset * -1)

        # Delete original sketch entities
        sketch_entity: adsk.fusion.SketchEntity
        for sketch_entity in loop_collection:
            sketch_entity.deleteMe()

    return sketch


def export_face_as_dxf(face, offset_option, offset_value) -> str:
    ao = apper.AppObjects()
    root_comp = ao.root_comp
    sketches = root_comp.sketches

    if offset_option:
        sketch = make_offset_sketch(face, offset_value)
    else:
        sketch = sketches.add(face)

    file_name = get_file_name(face, 'dxf')
    sketch.saveAsDXF(file_name)
    sketch.deleteMe()
    return file_name


def name_check(name, counter) -> str:
    if os.path.exists(name):
        new_name = f'{name[:name.rfind("_")]}_{counter}.{name[-3:]}'
        counter += 1
        name = name_check(new_name, counter)

    return name


def get_file_name(face: adsk.fusion.BRepFace, extension) -> str:
    name = f'{face.body.parentComponent.partNumber}-{face.body.name}_0.{extension}'
    new_name = os.path.join(get_output_path(), name)

    name = name_check(new_name, 1)

    return name


def get_output_path() -> str:
    ao = apper.AppObjects()
    dir_name = f'{ao.document.dataFile.name}'
    output_path = os.path.join(apper.get_default_dir(config.app_name), dir_name, "")

    # Create the folder if it does not exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    return output_path


def build_common_inputs(inputs: adsk.core.CommandInputs):
    ao = apper.AppObjects()

    # doc_name = ao.document.name
    # default_file_name = os.path.join(apper.get_default_dir(config.app_name), doc_name)
    # inputs.addStringValueInput('file_name_input', 'File Name: ', default_file_name)

    selection_input = inputs.addSelectionInput('faces', 'Select Faces: ', 'Select faces to add to dxf output')
    selection_input.addSelectionFilter('PlanarFaces')
    selection_input.setSelectionLimits(1, 0)

    inputs.addBoolValueInput('offset_option', 'Create Offset', True, '', True)

    offset_value = adsk.core.ValueInput.createByReal(config.default_offset)
    units = ao.units_manager.defaultLengthUnits
    offset_value = inputs.addValueInput('offset_value', 'Offset Value', units, offset_value)
    offset_value.tooltip = 'Adjust for Kerf width for Laser and Water Jet applications'
    offset_value.tooltipDescription = '<br><h2>Note!</h2><br>' \
                                      'Offset value is the amount of offset applied outwards to the existing edges' \
                                      '<br>' \
                                      '<i>For a laser cutter this would typically be defined as: kerf / 2</i>'


def build_dxf_export_inputs(inputs: adsk.core.CommandInputs):
    inputs.addBoolValueInput('dxf_combine_option', 'Combine to single DXF?', True, '', True)

    dxf_option_title = inputs.addTextBoxCommandInput('dxf_option_title', '', 'Face organization', 1, True)
    dxf_option_title.isVisible = True

    dxf_option_group = inputs.addRadioButtonGroupCommandInput('dxf_option_group', '')
    dxf_option_group.listItems.add('Blocks', True)
    dxf_option_group.listItems.add('Layers', False)
    dxf_option_group.listItems.add('Flat', False)
    dxf_option_group.isVisible = True

    dxf_warning_text = '<br><h3>Note!</h3><br>' \
                       'All faces will be moved to origin in output DXF<br><br>' \
                       '<i>Depending on orientation of the face, the results may be unpredictable</i>'
    dxf_warning = inputs.addTextBoxCommandInput('dxf_warning', '', dxf_warning_text, 10, True)
    dxf_warning.isVisible = True


def update_dxf_combine_option(inputs: adsk.core.CommandInputs):
    dxf_option_group = inputs.itemById('dxf_option_group')
    dxf_warning = inputs.itemById('dxf_warning')
    dxf_option_title = inputs.itemById('dxf_option_title')
    dxf_combine_option: adsk.core.BoolValueCommandInput = inputs.itemById('dxf_combine_option')

    if dxf_combine_option.value:
        dxf_option_group.isVisible = True
        dxf_warning.isVisible = True
        dxf_option_title.isVisible = True
    else:
        dxf_option_group.isVisible = False
        dxf_warning.isVisible = False
        dxf_option_title.isVisible = False


class DXFExportCommand(apper.Fusion360CommandBase):

    def on_execute(self, command, inputs, args, input_values):
        ao = apper.AppObjects()

        dxf_option = input_values['dxf_option_group']
        dxf_combine_option = input_values['dxf_combine_option']
        offset_option = input_values['offset_option']
        offset_value = input_values['offset_value']

        target_drawing = create_empty_dxf()

        face: adsk.fusion.BRepFace
        for face in input_values['faces']:
            dxf_file = export_face_as_dxf(face, offset_option, offset_value)

            if dxf_combine_option:
                add_to_dxf(dxf_file, dxf_option, target_drawing)
                os.remove(dxf_file)

        if dxf_combine_option:
            file_path = get_output_path()
            file_name = f'{file_path[:-1]}.dxf'
            target_drawing.saveas(file_name)

            ao.ui.messageBox(f'DXF File exported to: <br>{file_name}')

        else:
            ao.ui.messageBox(f'All DXF Files were exported to: <br>{get_output_path()}')

    def on_create(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):
        build_common_inputs(inputs)
        build_dxf_export_inputs(inputs)

    def on_input_changed(self, command, inputs: adsk.core.CommandInputs, changed_input, input_values):
        if changed_input.id == 'dxf_combine_option':
            update_dxf_combine_option(inputs)


class PDFExportCommand(apper.Fusion360CommandBase):

    def on_execute(self, command, inputs, args, input_values):
        offset_option = input_values['offset_option']
        offset_value = input_values['offset_value']

        face: adsk.fusion.BRepFace
        for face in input_values['faces']:
            dxf_file = export_face_as_dxf(face, offset_option, offset_value)
            export_pdf(dxf_file)
            os.remove(dxf_file)

    def on_create(self, command: adsk.core.Command, inputs: adsk.core.CommandInputs):

        build_common_inputs(inputs)
