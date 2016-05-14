from __future__ import division
from __future__ import absolute_import
from __future__ import print_function

import os
import os.path
import time

from .errors import *


class W1Device(object):

    def __init__(self, family, serial, w1_dir):
        self.w1_dir = w1_dir
        self.serial = serial
        self.family = family

        self._rw_fh = None
        self._reopen_fh()

    def _reopen_fh(self):
        if self._rw_fh:
            self._rw_fh.close()
        rw_path = os.path.join(self.w1_dir, 'rw')
        self._rw_fh = open(rw_path, 'a+b', buffering=0)

    def cmd(self, command, data='', response_size=0,
            wait_for_nonzero=False, wait_backoff_func=None, timeout=3):
        start = time.time()
        for i in range(10):
            try:
                self._rw_fh.write(chr(command) + data)
                break

            except IOError:
                self._reopen_fh()

        if wait_for_nonzero:
            iteration = 1
            while True:
                data_byte = self._rw_fh.read(1)
                if data_byte and ord(data_byte):
                    return

                if timeout is not None and (time.time() - start) > timeout:
                    raise Timeout()

                if wait_backoff_func is not None:
                    time.sleep(wait_backoff_func(iteration))
                iteration += 1
        
        elif response_size:
            return self._rw_fh.read(response_size)

        return
