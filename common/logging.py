# @Author:   Ben Sokol
# @Email:    git@bensokol.com
#
# Copyright (C) 2022 by Ben Sokol. All Rights Reserved.

import logging
import pathlib
import sys
import typing

handlers: typing.Dict[str, logging.Handler] = {}


class Logging(object):
    @staticmethod
    def setup_logfile(log_file: str):
        """ Add log file to logging """
        log_path = pathlib.Path(log_file)
        log_filename = log_path.name
        log_dir = log_path.parent

        if log_dir and not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        logfile = logging.FileHandler(log_file, 'w')
        logfile.setFormatter(formatter)

        logger = logging.getLogger()
        logger.addHandler(logfile)
        handlers[log_filename] = logfile

    @staticmethod
    def remove_logfile(log_file: str):
        """ Remove log file from logging """
        log_filename = pathlib.Path(log_file).name
        logger = logging.getLogger()
        success = False
        if log_filename in handlers:
            file_handler = handlers.pop(log_filename, None)
            if file_handler is not None:
                logger.removeHandler(file_handler)
                success = True
        return success

    @staticmethod
    def setup(level: int = logging.INFO, out_level: int = logging.INFO, err_level: int = logging.ERROR):
        """ Setup stdout and stderr for logging. Set logging level to INFO. """
        logger = logging.getLogger()
        formatter = Logging.Formatter()

        out_stream = logging.StreamHandler(sys.stdout)
        out_stream.setFormatter(formatter)
        out_stream.setLevel(out_level)
        out_stream.addFilter(Logging.Stdout_Filter())
        logger.addHandler(out_stream)
        handlers["stdout"] = out_stream

        err_stream = logging.StreamHandler(sys.stderr)
        err_stream.setFormatter(formatter)
        err_stream.setLevel(err_level)
        logger.addHandler(err_stream)
        handlers["stderr"] = err_stream

        logger.setLevel(level)

    class Formatter(logging.Formatter):
        BASE_FORMAT = '%(levelname)s: %(message)s'
        INFO_FORMAT = '%(message)s'

        FILE_FORMAT = '%(file)s(%(line)s): '

        def format(self, record: logging.LogRecord):
            if 'file' in record.__dict__:
                self._fmt = self.FILE_FORMAT
            else:
                self._fmt = ''

            if record.levelno == logging.INFO:
                self._fmt += self.INFO_FORMAT
            else:
                self._fmt += self.BASE_FORMAT

            return logging.Formatter.format(self, record)

    class Stdout_Filter(logging.Filter):
        def filter(self, record: logging.LogRecord):
            if record.levelno > logging.WARNING:
                # Don't log errors to stdout. They'll get
                # logged to stderr
                return False
            else:
                return True
