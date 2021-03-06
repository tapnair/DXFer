# Purpose: drawing module
# Created: 11.03.2011
# Copyright (C) 2011, Manfred Moitzi
# License: MIT License
from __future__ import unicode_literals
__author__ = "mozman <mozman@gmx.at>"

from datetime import datetime
import io
import warnings

from . import database
from .lldxf.tags import DXFTag, write_tags
from .lldxf.const import DXFVersionError, acad_release, BLK_XREF
from .lldxf.tagger import stream_tagger
from .dxffactory import dxffactory
from .templates import TemplateLoader
from .options import options
from .tools.codepage import tocodepage, toencoding
from .sections import Sections
from .tools.juliandate import juliandate
from .lldxf import repair
from .audit import Audit


class Drawing(object):
    """ The Central Data Object
    """
    def __init__(self, tagreader):
        """ Create a new drawing. """

        self._is_binary_data_compressed = False
        self.comments = []  # list of comment strings - saved as (999, comment) tags on top of file
        self.dxffactory = None  # readonly - set by _bootstraphook()
        self.dxfversion = 'AC1009'  # readonly - set by _bootstraphook()
        self.encoding = 'cp1252'  # read/write - set by _bootstraphook()
        self.filename = None  # read/write
        self.entitydb = database.factory()
        self.sections = Sections(tagreader, self)
        self._groups = None
        if self.dxfversion > 'AC1009':
            self.rootdict = self.objects.rootdict
            self.objects.setup_objects_management_tables(self.rootdict)  # create missing tables
            if self.dxfversion in ('AC1012', 'AC1014'):  # releases R13 and R14
                repair.upgrade_to_ac1015(self)
            # some applications don't setup properly the 'Model' and paper space layouts
            repair.setup_layouts(self)
            self._groups = self.objects.groups()
        else:
            if self.dxfversion < 'AC1009':  # legacy DXF version
                repair.upgrade_to_ac1009(self)  # upgrade to DXF format AC1009 (DXF R12)
            if repair.is_leica_disto_r12(self):  # check for malformed DXF R12 files by Leica Disto Units
                repair.repair_leica_disto_r12(self)
            repair.enable_handles(self)

        self.layouts = self.dxffactory.get_layouts()

        if self.dxfversion > 'AC1009':
            # for ProE, which writes entities without owner tags (330)
            self.entities.repair_model_space(self.modelspace().layout_key)
            self.layouts.link_block_entities_into_layouts()

        if options.compress_binary_data:
            self.compress_binary_data()

    def compress_binary_data(self):
        if self.dxfversion > 'AC1009' and not self._is_binary_data_compressed:
            self.entitydb.compress_binary_data()
            self._is_binary_data_compressed = True

    @property
    def acad_release(self):
        return acad_release.get(self.dxfversion, "unknown")

    @property
    def _handles(self):
        return self.entitydb.handles

    def _bootstraphook(self, header, comments):
        # called from HeaderSection() object to update important dxf properties
        # before processing sections, which depends from this properties.
        self.comments = comments  # preserve leading file comments
        self.dxfversion = header.get('$ACADVER', 'AC1009')
        seed = header.get('$HANDSEED', str(self._handles))
        self._handles.reset(seed)
        codepage = header.get('$DWGCODEPAGE', 'ANSI_1252')
        self.encoding = toencoding(codepage)
        self.dxffactory = dxffactory(self)

    @property
    def is_binary_data_compressed(self):
        return self._is_binary_data_compressed

    @property
    def header(self):
        return self.sections.header

    @property
    def layers(self):
        return self.sections.tables.layers

    @property
    def linetypes(self):
        return self.sections.tables.linetypes

    @property
    def styles(self):
        return self.sections.tables.styles

    @property
    def dimstyles(self):
        return self.sections.tables.dimstyles

    @property
    def ucs(self):
        return self.sections.tables.ucs

    @property
    def appids(self):
        return self.sections.tables.appids

    @property
    def views(self):
        return self.sections.tables.views

    @property
    def block_records(self):
        return self.sections.tables.block_records

    @property
    def viewports(self):
        return self.sections.tables.viewports

    @property
    def blocks(self):
        return self.sections.blocks

    @property
    def groups(self):
        if self._groups is not None:
            return self._groups
        else:
            raise Warning('Not supported for DXF version AC1009.')

    def modelspace(self):
        return self.layouts.modelspace()

    def layout(self, name=None):
        return self.layouts.get(name)

    def layout_names(self):
        return list(self.layouts.names())

    def delete_layout(self, name):
        if self.dxfversion > 'AC1009':
            if name not in self.layouts:
                raise ValueError("Layout '{}' does not exist.".format(name))
            else:
                self.layouts.delete(name)
        else:
            raise Warning('Not supported for DXF version AC1009.')

    def new_layout(self, name, dxfattribs=None):
        if self.dxfversion > 'AC1009':
            if name in self.layouts:
                raise ValueError("Layout '{}' already exists.".format(name))
            else:
                return self.layouts.new(name, dxfattribs)
        else:
            raise Warning('Not supported for DXF version AC1009.')

    def get_active_layout_key(self):
        if self.dxfversion > 'AC1009':
            for name in ('*Paper_Space', '*PAPER_SPACE'):
                try:
                    active_layout_block_record = self.block_records.get(name)
                    return active_layout_block_record.dxf.handle
                except ValueError:
                    pass
            return None
        else:
            return self.layout().layout_key  # AC1009 supports just one layout and this is the active one

    def get_active_entity_space_layout_keys(self):
        layout_keys = [self.modelspace().layout_key]
        active_layout_key = self.get_active_layout_key()
        if active_layout_key is not None:
            layout_keys.append(active_layout_key)
        return layout_keys

    @property
    def entities(self):
        return self.sections.entities

    @property
    def objects(self):
        return self.sections.objects

    def get_dxf_entity(self, handle):
        """ Get entity by *handle* from entity database.

        Low level access to DXF entities database. Raises *KeyError* if handle don't exists.
        Returns DXFEntity() or inherited.

        If you just need the raw DXF tags use::

            tags = Drawing.entitydb[handle]  # raises KeyError, if handle don't exist
            tags = Drawing.entitydb.get(handle)  # returns a default value, if handle don't exist (None by default)

        type of tags: ClassifiedTags()
        """
        return self.dxffactory.wrap_handle(handle)

    def add_image_def(self, filename, size_in_pixel, name=None):
        """ Add an image definition to the objects section.

        :param filename: image file name
        :param size_in_pixel: image size in pixel as (x, y) tuple
        :param name: image name for internal use, None for an auto-generated name
        """
        if self.dxfversion < 'AC1015':
            raise DXFVersionError('The IMAGE entity needs at least DXF version AC1015 (R2000) or later.')
        return self.objects.add_image_def(filename, size_in_pixel, name)

    def add_underlay_def(self, filename, format='ext', name=None):
        """ Add an underlay definition to the objects section.

        :param format: file format as string pdf|dwf|dgn or ext=get format from filename extension
        :param name: underlay name, None for an auto-generated name
        """
        if self.dxfversion < 'AC1015':
            raise DXFVersionError('The UNDERLAY entity needs at least DXF version AC1015 (R2000) or later.')
        if format == 'ext':
            format=filename[-3:]
        return self.objects.add_underlay_def(filename, format, name)

    def add_xref_def(self, filename, name, flags=BLK_XREF):
        """ Add an external reference (xref) definition to the blocks section.

        Add xref to a layout by `layout.add_blockref(name, insert=(0, 0))`.

        :param filename: external reference filename
        :param name: name of the xref block
        """
        self.blocks.new(name=name, dxfattribs={
            'flags': flags,
            'xref_path': filename
        })

    def _get_encoding(self):
        codepage = self.header.get('$DWGCODEPAGE', 'ANSI_1252')
        return toencoding(codepage)

    @staticmethod
    def new(dxfversion='AC1009'):
        from .lldxf.const import versions_supported_by_new, acad_release_to_dxf_version

        dxfversion = dxfversion.upper()
        dxfversion = acad_release_to_dxf_version.get(dxfversion, dxfversion)  # translates 'R12' -> 'AC1009'
        if dxfversion not in versions_supported_by_new:
            raise DXFVersionError("Can not create DXF drawings, unsupported DXF version '{}'.".format(dxfversion))
        finder = TemplateLoader(options.template_dir)
        stream = finder.getstream(dxfversion.upper())
        try:
            dwg = Drawing.read(stream)
        finally:
            stream.close()
        dwg._setup_metadata()
        return dwg

    def _setup_metadata(self):
        self.header['$TDCREATE'] = juliandate(datetime.now())

    @staticmethod
    def read(stream):
        """ Open an existing drawing. """
        tagreader = stream_tagger(stream)
        return Drawing(tagreader)

    def saveas(self, filename, encoding='auto'):
        self.filename = filename
        self.save(encoding=encoding)

    def save(self, encoding='auto'):
        # DXF R12, R2000, R2004 - ASCII encoding
        # DXF R2007 and newer - UTF-8 encoding
        if encoding == 'auto':
            enc = 'utf-8' if self.dxfversion >= 'AC1021' else self.encoding
        else:  # override default encoding, for applications that handles encoding different than AutoCAD
            enc = encoding
        # in ASCII mode unknown, characters will be escaped as \U+nnnn unicode characters.
        with io.open(self.filename, mode='wt', encoding=enc, errors='dxfreplace') as fp:
            self.write(fp)

    def write(self, stream):
        self._create_appids()
        self._update_metadata()
        if options.store_comments:
            self.write_leading_comments(stream)
        self.sections.write(stream)

    def write_leading_comments(self, stream):
        comment_tags = (DXFTag(999, comment) for comment in self.comments)
        write_tags(stream, comment_tags)

    def cleanup(self, groups=True):
        """
        Cleanup drawing. Call it before saving the drawing but only if necessary, the process could take a while.

        Args:
            groups (bool): removes deleted and invalid entities from groups
        """
        if groups and self.groups is not None:
            self.groups.cleanup()

    def audit(self):
        """
        Audit drawing for DXF structure errors like undefined line types.

        Returns:
            Auditor() object

        """
        auditor = Audit(self)
        auditor.run()
        return auditor

    def _update_metadata(self):
        now = datetime.now()
        self.header['$TDUPDATE'] = juliandate(now)
        self.header['$HANDSEED'] = str(self._handles)
        self.header['$DWGCODEPAGE'] = tocodepage(self.encoding)
        self._update_comments(now)

    def _update_comments(self, now):
        from . import VERSION
        # remove existing ezdxf comments
        self.comments = [comment for comment in self.comments if not comment.startswith('last saved by ezdxf')]
        self.comments.append("last saved by ezdxf {} on {}".format(VERSION, now.strftime("%Y-%m-%d %H:%M:%S")))

    def _create_appids(self):
        def create_appid_if_not_exist(name, flags=0):
            if name not in self.appids:
                self.appids.new(name, {'flags': flags})

        if self.dxfversion > 'AC1009':
            create_appid_if_not_exist('HATCHBACKGROUNDCOLOR', 0)

