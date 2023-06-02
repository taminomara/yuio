import logging as _logging
import os as _os

_logger = _logging.getLogger('yuio.internal')
_logger.propagate = 'YUIO_DEBUG' in _os.environ
