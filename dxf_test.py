

import sys
import os

# Todo add and remove ass necessary only when making the call
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import ezdxf


def main():
    # base_file = 'nRF52832_MCU-multiple'
    base_file = 'nRF52832_MCU'
    # input_file = 'Notch_tag_example'

    file_name = os.path.join(os.path.dirname(__file__), base_file + '.dxf')

    dwg = ezdxf.readfile(file_name)
    modelspace = dwg.modelspace()

    print('opened   ' + dwg.dxfversion)



    blockrefs = modelspace.query('INSERT')

    # for block in blockrefs:
    #     print(block.dxf.name)
    #     entities = block.query('*')

    blocks = dwg.blocks
    #

    old_entities = modelspace.query('*')

    # print('Old Stuff \n\n')
    # for entity in old_entities:
    #     # if entity.dxf.layer == '1_copper':
    #     print(entity.dxftype)
    #     print(entity.dxf.layer)

    # for block in blocks:
    #     print(block.name)
    #     entities = block.query('*')
    #
    #     for entity in entities:
    #         print(entity.dxftype)
    #         print(entity.dxf.layer)
    #         if entity.dxf.layer == 'NOTCHTAG':
    #             print('NOTCHTAG')
    #             print(entity.dxftype)
    #             print(entity.dxf.text)
    #             print(entity.dxf.insert)
    #         if entity.dxf.layer == 'NOTCH':
    #             print('NOTCH')
    #             print(entity.dxftype)
    #             print(entity.dxf.start)
    #             print(entity.dxf.end)
    #
    #         block.unlink_entity(entity)
    #         modelspace.add_entity(entity)

    print('\n\nNew Stuff \n\n')

    print(len(dwg.sections.tables.layers))
    for layer in dwg.layers:
        print(layer.dxf.name)
        new_string = layer.dxf.name.replace('.', '_')
        new_string = new_string('/', '_')
        new_string = new_string('\\', '_')
        layer.dxf.name = new_string



    new_entities = modelspace.query('*')

    # for entity in new_entities:
    #     print(entity.dxftype)
    #     print(entity.dxf.layer)

    new_file_name = os.path.join(os.path.dirname(__file__), base_file + '_exploded.dxf')

    dwg.saveas(new_file_name)

if __name__ == '__main__':
    main()