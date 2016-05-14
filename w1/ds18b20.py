from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import struct

from .crc import do_crc
from .errors import W1Error, WrongCRC, WriteError
from .w1_device import W1Device


class DS18B20Resolution(int):

    def __new__(cls, value=None):
        if value is not None:
            obj = int.__new__(cls, value)
            if obj < 9 or obj > 12:
                raise ValueError('Resolution should be within 9-12 bits')
            return obj

    @classmethod
    def from_conf(cls, conf):
        if conf > 127:
            raise ValueError('Invalid configuration value')
        return cls(9 + (conf >> 5))

    def to_conf(self):
        return ((self - 9) << 5) | 0b11111


class DS18B20Data(object):
    
    __slots__ = (
        'temperature',
        'th',
        'tl',
        'resolution',
    )

    def __init__(self, raw_data=None):
        self.temperature = self.th = self.tl = self.resolution = None
        if raw_data is not None:
            self.load_data(raw_data)

    def load_data(self, raw_data):
        if len(raw_data) != 9:
            raise WrongCRC()
        fields = struct.unpack('<hbbBBBBB', raw_data)
        temp, self.th, self.tl, conf, _, _, _, crc = fields
        if crc != do_crc(raw_data[:-1]):
            raise WrongCRC()

        self.temperature = temp / 2**4
        self.resolution = DS18B20Resolution.from_conf(conf)

    def __repr__(self):
        return repr(dict([(field, getattr(self, field)) for field in self.__slots__]))


class DS18B20(W1Device):

    FAMILY = 0x28

    # Commands
    CONVERT_T = 0x44
    WRITE_SCRATCHPAD = 0x4E
    READ_SCRATCHPAD = 0xBE
    COPY_SCRATCHPAD = 0x48
    RECALL_E2 = 0xB8

    def __init__(self, family, serial, w1_dir):
        super(DS18B20, self).__init__(family, serial, w1_dir)
        self.resolution = None
        try:
            self.resolution = self.read_data().resolution

        except W1Error:
            pass

    def convert(self):
        if self.resolution is not None:
            resolution = self.resolution
        else:
            resolution = 9
        convert_time = 750 / 2 ** (12 - resolution)

        def backoff_func(iteration):
            if iteration > 10:
                return 0.001
            sleep_ms = convert_time / 2**iteration
            return max(sleep_ms, 1) / 1000

        self.cmd(
            self.CONVERT_T,
            wait_for_nonzero=True,
            wait_backoff_func=backoff_func,
        )

    def read_data(self, tries=1):
        while tries > 0:
            try:
                res = self.cmd(self.READ_SCRATCHPAD, response_size=9)
                data = DS18B20Data(res)
                self.resolution = data.resolution
                return data
            except W1Error as exc:
                print('Error: %r, retrying...' % (exc,))
                tries -= 1
                if tries <= 0:
                    raise

    def write_data(self, th=None, tl=None, resolution=None):
        if th is None and tl is None and resolution is None:
            raise ValueError('None of values is set')
        prev_data = self.read_data(tries=16)
        
        if th is None:
            th = prev_data.th

        if tl is None:
            tl = prev_data.tl

        if resolution is None:
            resolution = prev_data.resolution

        raw_data = struct.pack('<bbB', th, tl, resolution.to_conf())

        for i in range(16):
            self.cmd(self.WRITE_SCRATCHPAD, raw_data, wait_for_nonzero=True)
            data = self.read_data(tries=16)
            if data.th != th or data.tl != tl or data.resolution != resolution:
                print("Wrong data read back: %d, %d, %d != %d, %d, %d" % (
                    data.th, data.tl, data.resolution,
                    th, tl, resolution,
                ))
                continue
            return

        raise WriteError('Wrong data were read back')

    def store(self):
        self.cmd(self.COPY_SCRATCHPAD, wait_for_nonzero=True)

    def restore(self):
        self.cmd(self.RECALL_E2, wait_for_nonzero=True)

    def measure(self, tries=None):
        self.convert()
        read_params = {}
        if tries is not None:
            read_params['tries'] = tries
        return self.read_data(**read_params).temperature
