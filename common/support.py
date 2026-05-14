# @Author:   Ben Sokol
# @Email:    git@bensokol.com
#
# Copyright (C) 2022 by Ben Sokol. All Rights Reserved.

import datetime
import enum
import importlib.util
import logging
import pathlib
import re
import subprocess
import sys
import threading
import time
import typing
import itertools


class ReturnCode(enum.IntEnum):
  """Return codes used by the support utilities.

  Attributes:
    success: Indicates successful completion.
    error: Indicates an error condition.
    warning: Indicates a warning condition.
    exception: Indicates an exception condition.
  """
  success = 0
  error = 1
  warning = 2
  exception = 3


# Compile regex patterns once at module level
_YES_PATTERN = re.compile(r'[yY]([eE][sS])?')
_NO_PATTERN = re.compile(r'[nN][oO]?')


def import_from_path(module_name: str, module_path: pathlib.Path):
  """Import a Python module from a file system path.

  Args:
    module_name: The module name to assign in sys.modules.
    module_path: The file path to the module source.

  Returns:
    The imported module, or None if the import failed.
  """
  spec = importlib.util.spec_from_file_location(module_name, module_path)
  if spec is None or spec.loader is None:
    logging.error(f"Unable to import module {module_name} from '{module_path}'")
    return

  module = importlib.util.module_from_spec(spec)
  sys.modules[module_name] = module
  spec.loader.exec_module(module)
  return module


def get_process_time():
  """Return the current process time for elapsed-time measurement.

  Returns:
    The current process time in seconds.
  """
  return time.perf_counter()


def get_duration(start: float, end: float):
  """Compute a human-readable duration string from start and end times.

  Args:
    start: The starting time in seconds.
    end: The ending time in seconds.

  Returns:
    A formatted duration string (HH:MM:SS).
  """
  duration = end - start
  return str(datetime.timedelta(seconds=duration))[:-4]


def get_user_confirmation(prompt: str = "Would you like to continue [y/n]: ", invalid_response_default: typing.Union[bool, None] = None):
  """Prompt the user for yes/no confirmation.

  Args:
    prompt: The message displayed for user input.
    invalid_response_default: Value to return when response is invalid.

  Returns:
    True for yes, False for no, or invalid_response_default when supplied.
  """
  while True:
    result = input(prompt)
    if _YES_PATTERN.match(result):
      return True
    elif _NO_PATTERN.match(result):
      return False
    else:
      if invalid_response_default is not None:
        return invalid_response_default
      else:
        logging.warning("Invalid response.")


def wait_for_user(prompt: str = "Press Enter to continue..."):
  """Pause execution until the user presses Enter.

  Args:
    prompt: The message shown before waiting for Enter.

  Returns:
    True once the user presses Enter.
  """
  sys.stdout.write(prompt)
  input()
  return True


def natsort(lst: typing.List[typing.Any]):
  """Sort a list using natural ordering.

  Args:
    lst: A list of values that can be compared as natural strings.

  Returns:
    A new list sorted using numeric parts within strings correctly.
  """
  def convert(text: str) -> typing.Union[int, str]:
    return int(text) if text.isdigit() else text.lower()

  def alphanum_key(key: typing.Any):
    return [convert(c) for c in re.split('([0-9]+)', key)]
  return sorted(lst, key=alphanum_key)


def subprocess_call(cmd: typing.Union[str, typing.List[str]], shell: bool = False, input_str: typing.Union[str, None] = None, noexec: bool = False, progress: bool = False, progress_message: str | None = None):
  """Run a subprocess command and optionally show progress.

  Args:
    cmd: The command string or list to execute.
    shell: Whether to run the command in the shell.
    input_str: Optional string to pass to subprocess stdin.
    noexec: If True, print the command instead of executing it.
    progress: If True, show a spinner while the command runs.
    progress_message: Optional message to show while running.

  Returns:
    The subprocess return code.
  """
  if noexec:
    print(cmd)
    return 0

  if not progress:
    if input_str is None:
      p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)
    else:
      p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, input=input_str.encode(encoding="ascii"), shell=shell)

    output = p.stdout.decode()
    if output:
      print(output)
    return p.returncode

  message = progress_message or "Running command"
  spinner = itertools.cycle("|/-\\")
  p = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    stdin=subprocess.PIPE if input_str is not None else subprocess.DEVNULL,
    shell=shell,
    text=True,
    bufsize=1,
  )

  def _read_output(stdout: typing.TextIO) -> None:
    for line in stdout:
      print(line.rstrip())

  reader = threading.Thread(target=_read_output, args=(p.stdout,), daemon=True)
  reader.start()

  sys.stdout.write(f"{message} ")
  sys.stdout.flush()
  while p.poll() is None:
    sys.stdout.write(next(spinner))
    sys.stdout.flush()
    time.sleep(0.1)
    sys.stdout.write("\b")
  reader.join()
  sys.stdout.write("\n")
  return p.returncode

