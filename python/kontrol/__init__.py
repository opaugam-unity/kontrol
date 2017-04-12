import logging

from logging.config import fileConfig
from os.path import dirname

#: our package version
__version__ = '0.0.1'

#
# - load our logging configuration from the local log.cfg resource
#
fileConfig('%s/log.cfg' % dirname(__file__), disable_existing_loggers=False)