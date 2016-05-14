from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import os
import os.path
import struct

from .w1_device import W1Device
from .ds18b20 import DS18B20
from .crc import do_crc
from .errors import WrongCRC

SLAVE_DRIVER_PATH = '/sys/bus/w1/drivers/w1_slave_driver/'

FAMILIES = {
    DS18B20.FAMILY: DS18B20,
}


def devices():
    dev_list = []
    for item in os.listdir(SLAVE_DRIVER_PATH):
        full_path = os.path.join(SLAVE_DRIVER_PATH, item)
        if not os.path.isdir(full_path):
            continue
        
        id_path = os.path.join(full_path, 'id')
        if not os.path.exists(id_path):
            continue

        id_fh = open(id_path, 'rb')
        full_id = id_fh.read()
        id_fh.close()

        family, ls_serial, ms_serial, crc = struct.unpack('<BHIB', full_id)
        serial = (ms_serial << 16) + ls_serial

        if crc != do_crc(full_id[:-1]):
            raise WrongCRC()

        dev_class = FAMILIES.get(family, W1Device)
        dev_list.append(dev_class(family, serial, full_path))

    return dev_list
