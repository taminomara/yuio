import logging
import os

_logger = logging.getLogger('yuio.internal')

if 'YUIO_DEBUG' in os.environ:
    _logger.setLevel(logging.DEBUG)
else:
    _logger.setLevel(logging.CRITICAL)
