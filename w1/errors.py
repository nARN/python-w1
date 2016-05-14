from __future__ import division
from __future__ import absolute_import
from __future__ import print_function


class W1Error(Exception):
    pass


class WrongCRC(W1Error):
    pass


class WriteError(W1Error):
    pass


class Timeout(W1Error):
    pass
