#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 - cologler <skyoflw@gmail.com>
# ----------
#
# ----------

import os
import sys
import traceback
import piexif
import re
from datetime import (datetime, timedelta)

DateTimeOriginalId = 36867

IGNORED_PROPERTIES = [
    'ImageWidth', 'ImageLength', 'BitsPerSample', 'ColorSpace',
    'XResolution', 'YResolution', 'ResolutionUnit', 'SamplesPerPixel',
    'Orientation', 'ExifVersion', 'PhotometricInterpretation',
    'JPEGInterchangeFormatLength', 'ExifTag', 'PixelXDimension',
    'Software', 'JPEGInterchangeFormat', 'Compression', 'PixelYDimension',
    'Make', 'Model', 'YCbCrPositioning', 'ExposureMode',
    'GPSTag', 'ExposureTime', 'FlashpixVersion', 'DigitalZoomRatio',
    'FNumber', 'SceneCaptureType', 'WhiteBalance',
    'ISOSpeedRatings', 'SubSecTimeOriginal', 'SubSecTimeDigitized',
    'ComponentsConfiguration',
    'ShutterSpeedValue',
    'ApertureValue',
    'ExposureBiasValue',
    'MeteringMode',
    'LightSource',
    'Flash',
    'MakerNote',
]

class ImagesManager:
    def __init__(self):
        self._ignored_properties = set(IGNORED_PROPERTIES)
        self._images = []
        dtregex = re.compile(r'^([\d]{4}):([\d]{2}):([\d]{2}) ([\d]{2}):([\d]{2}):([\d]{2})$')
        self._tags_regexs = {
            'DateTime': dtregex,
            'DateTimeOriginal': dtregex,
            'DateTimeDigitized': dtregex,
        }
        self._ignore_exts = set()

    @property
    def ignored_properties(self):
        return self._ignored_properties

    @property
    def tags_regexs(self):
        return self._tags_regexs

    def add(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.bmp'):
            self._ignore_exts.add(ext)
            return
        try:
            assert os.path.isfile(path)
            holder = ImageHolder(self, path)
        except Exception as e:
            print('Cannot load file: %s' % path)
            raise
        self._images.append(holder)

    def complete(self):
        if len(self._ignore_exts) > 0:
            for ext in self._ignore_exts:
                print('ignore ext: %s' % ext)
            input('continue?')
        od = self._images[0].origin_datetime
        if od is None:
            dt = datetime.now()
        else:
            m = od[2]
            dtargs = [int(x) for x in m.groups()]
            dt = datetime(*dtargs)
        for i, t in enumerate(self._images):
            t.set_datetime(dt, i)
        for t in self._images:
            t.save()

class ImageHolder:
    def __init__(self, manager, path):
        self._manager = manager
        self._path = path
        self._exifs = piexif.load(path)
        self._exif = self._exifs['Exif']
        self._tags = {}
        self._unknownd_tags = []

        for ifd in self._exifs:
            if ifd == 'thumbnail':
                continue
            ex = self._exifs[ifd]
            for tagid in ex:
                name = piexif.TAGS[ifd][tagid]["name"]
                value = ex[tagid]
                if name in self._manager.ignored_properties:
                    continue
                self.add_property(tagid, name, value)

        if len(self._unknownd_tags) > 0:
            ut = ['%s = %s' % x for x in self._unknownd_tags]
            raise NotImplementedError('Unknown tag: \n' + '\n'.join(ut))

        self._origin_datetime = self._tags.get('DateTimeOriginal') or\
                                self._tags.get('DateTimeDigitized') or\
                                self._tags.get('DateTime')

    @property
    def origin_datetime(self):
        return self._origin_datetime

    def add_property(self, tagid, name, value):
        regex = self._manager.tags_regexs.get(name)
        if regex is None:
            self._unknownd_tags.append((name, value))
            return
        if self._tags.get(name) != None:
            raise NotImplementedError
        value_str = value.decode('utf8')
        m = regex.match(value_str)
        if not m:
            raise NotImplementedError
        self._tags[name] = (tagid, value_str, m)

    def set_datetime(self, datetime, index):
        datetime = timedelta(0, index) + datetime
        self._exif[DateTimeOriginalId] = str(datetime).replace('-', ':').encode()

    def save(self):
        exif_bytes = piexif.dump(self._exifs)
        piexif.insert(exif_bytes, self._path)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        manager = ImagesManager()
        paths = sys.argv[1:]
        if len(paths) == 1:
            if os.path.isdir(paths[0]):
                paths = [os.path.join(paths[0], x) for x in os.listdir(paths[0])]
        for path in paths:
            manager.add(path)
        manager.complete()
    except Exception:
        traceback.print_exc()
        input()

if __name__ == '__main__':
    main()
