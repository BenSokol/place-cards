# @Author:   Ben Sokol
# @Email:    git@bensokol.com
#
# Copyright (C) 2026 by Ben Sokol. All Rights Reserved.

import argparse
import concurrent.futures
import logging
import itertools
import math
import os
import pathlib
import re
import sys
import typing
import unicodedata

from common import support
from common.logging import Logging

cwd = os.getcwd()
curdir = pathlib.Path(__file__).parent
card_model_file = curdir.joinpath('card.scad')
template_card_model_file = curdir.joinpath('template_card.scad')

default_cpu_count = math.floor((c * 1.5 if isinstance(c := os.cpu_count(), int) else 1))
default_openscad_path = "/opt/homebrew/bin/openscad"
default_outdir = "gen"
default_resolution = 64
default_text_resolution = 128

class Data:
  """Represents a single OpenSCAD generation job.

  Attributes:
    name: The display name for the generated output.
    path: The output file path for the generated STL.
    rel_path: The relative path for display and logging purposes.
    args: The command arguments passed to OpenSCAD.
    count: The index of this job in the full generation sequence.
    total: The total number of jobs being generated.
    name_ljust: Width used for pretty-printing the name column.
    path_ljust: Width used for pretty-printing the path column.
    noexec: If True, the command is printed but not executed.
  """
  def __init__(self, name: str, path: pathlib.Path, args: list[str], count: int = 1, total: int = 1, name_ljust: int = 0, path_ljust: int = 0, rel_path: pathlib.Path | None = None, noexec: bool = False):
    self.name = name
    self.path = path
    self.rel_path = rel_path or path
    self.args = args
    self.count = count
    self.total = total
    self.name_ljust = name_ljust
    self.path_ljust = path_ljust
    self.noexec = noexec


def main():
  """Parse command-line arguments, prepare generation jobs, and run OpenSCAD.

  This function handles template regeneration, name deduplication, output
  directory creation, and parallel execution of card exports.
  """
  parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)

  parser.add_argument('file', action='store', help="File containing line separated names.")

  generation_options = parser.add_argument_group("Generation Options")
  generation_options.add_argument('--openscad_path', action='store', help=f"Path to openscad (Default: {default_openscad_path})", default=default_openscad_path)
  generation_options.add_argument('-j', '--cpu_threads', action='store', type=int, help=f"Number of threads to use. (Default: {default_cpu_count})", default=default_cpu_count)
  generation_options.add_argument('-f', '--force_generate_template', action="store_true", default=False, help="Force regenerate template_card.stl, even if it already exists.")
  generation_options.add_argument('--only_generate_template', action="store_true", default=False, help="Only generates template_card.stl, if needed.  Combine with '-f' to force generation.")
  generation_options.add_argument('--openscad_quiet', action="store_true", default=False, help="Force openscad to be quiet.")
  generation_options.add_argument('--resolution', action='store', type=int, default=default_resolution, help=f"OpenSCAD polygon resolution ($fn) for generated models. (Default: {default_resolution})")
  generation_options.add_argument('--text_resolution', action='store', type=int, default=default_text_resolution, help=f"OpenSCAD polygon resolution for embossed text only. (Default: {default_text_resolution})")

  output_options = parser.add_argument_group("Output Options")
  output_options.add_argument('-o', '--outdir', action="store", help=f"Output Directory. (Default: {default_outdir})", default=default_outdir)
  output_subdir_options = output_options.add_mutually_exclusive_group()
  output_subdir_options.add_argument('--outdir_by_letter', action="store", type=int, default=None, metavar='N', help="Sort output into subdirectories using first N characters of each name (for example gen/a, gen/ab). (Default: disabled)")
  output_subdir_options.add_argument('--outdir_by_count', action="store", default=0, type=int, metavar='N', help=f"How many files are split into each subdirectory? If `0`, no subdirectories are used. (Default: 0)")

  debug_options = parser.add_argument_group("Debug options")
  debug_options.add_argument('-n', '--noexec', action="store_true", help="No execute.", default=False)
  debug_options.add_argument('--no-summary', action='store_true', default=False, help="Disable the final generation summary report.")
  verbose_quiet_mutex = debug_options.add_mutually_exclusive_group()
  verbose_quiet_mutex.add_argument('-v', '--verbose', action="store_const", help="Prints additional information.", const=logging.DEBUG, default=logging.INFO, dest='logging_verbosity')
  verbose_quiet_mutex.add_argument('-q', '--quiet', action="store_const", help="Hides all output except warnings and errors.", const=logging.WARNING, default=logging.INFO, dest='logging_verbosity')

  args = parser.parse_args()

  Logging.setup(level=args.logging_verbosity, out_level=args.logging_verbosity)
  logging.debug(args)
  is_quiet = args.logging_verbosity == logging.WARNING
  start_time = support.get_process_time()
  warning_count = 0
  error_count = 0

  if args.cpu_threads < 1:
    logging.error("CPU count must be > 0.")
    sys.exit(1)

  # Create root output directory if needed
  root_output_dir = pathlib.Path(args.outdir)
  root_output_dir.mkdir(parents=True, exist_ok=True)

  # Generate template_card.stl if needed
  template_card_stl = root_output_dir.joinpath('template_card.stl')
  should_regenerate_template = not template_card_stl.exists() or args.force_generate_template

  # Check if template_card.scad has been modified since template_card.stl was generated
  if not should_regenerate_template and template_card_model_file.exists():
    scad_mtime = template_card_model_file.stat().st_mtime
    stl_mtime = template_card_stl.stat().st_mtime
    should_regenerate_template = scad_mtime > stl_mtime
    if should_regenerate_template:
      logging.info(f"template_card.scad has been modified since template_card.stl was generated. Regenerating...")

  if should_regenerate_template:
    if args.force_generate_template:
      logging.info("Re-generating template_card.stl, this may take a few minutes...")
    else:
      logging.info("Generating template_card.stl, this may take a few minutes...")
    template_gen_args = build_openscad_command_arguments(
      args.openscad_path,
      template_card_stl,
      template_card_model_file,
      False,
      is_quiet or args.openscad_quiet,
      ['-D', f'resolution={args.resolution}'])
    template_data = Data("template_card.stl", template_card_stl, template_gen_args, rel_path=get_relative_path(template_card_stl), noexec=args.noexec)
    run_openscad_command(template_data, progess=True, progress_message="Generating template_card.stl")

  # Read in newline separated names, strip extra whitespace, generate output path
  names: list[typing.Tuple[int, str, pathlib.Path]] = []
  seen_names: set[str] = set()
  name_ljust = 0
  path_ljust = 0
  count = 0
  output_subdir = 0
  with open(args.file) as fp:
    for line in fp:
      # Strip whitespace/newlines
      name = line.strip()
      if not name:
        # Skip empty lines
        continue
      elif name not in seen_names:
        seen_names.add(name)
        output_dir = root_output_dir

        # If requested, sort output into subdirectories.
        if args.outdir_by_letter is not None:
          letter_dir = slugify(name)[:args.outdir_by_letter] or '_'
          output_dir = output_dir.joinpath(letter_dir)
        elif args.outdir_by_count > 0:
          if count % args.outdir_by_count == 0:
            output_subdir += 1
          output_dir = output_dir.joinpath(str(output_subdir))

        # Create output directory if needed.
        output_dir.mkdir(parents=True, exist_ok=True)

        # normalize output path
        output_path = output_dir.joinpath(f"{slugify(name)}.stl")
        logging.debug(f"Adding '{name}' with output path: '{output_path}'")
        names.append((count + 1, name, output_path))

        # Find longest name/path to ljust output
        name_ljust = max(name_ljust, len(name))
        path_ljust = max(path_ljust, len(str(get_relative_path(output_path))))

        # Increment count
        count += 1
      else:
        warning_count += 1
        logging.warning(f"Found duplicate name: '{name}'. Skipping...")

  # Generate openscad commands
  openscad_commands: list[Data] = []
  for (c, name, path) in names:
    gen_args: list[str] = build_openscad_command_arguments(
      args.openscad_path,
      path,
      card_model_file,
      True,
      is_quiet or args.openscad_quiet,
      ['-D', f'resolution={args.resolution}'],
      ['-D', f'text_resolution={args.text_resolution}'],
      ['-D', f'template_file="{template_card_stl}"'],
      ['-D', f'text="{name}"'])

    openscad_commands.append(Data(name, path, gen_args, c, len(names), name_ljust, path_ljust, rel_path=get_relative_path(path), noexec=args.noexec))

  # Generate cards
  if args.cpu_threads > 1:
    # Generate using threadpool
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.cpu_threads) as executor:
      results = list(executor.map(run_openscad_command, openscad_commands))
  elif args.cpu_threads == 1:
    # Generate without threadpool
    results = [run_openscad_command(command) for command in openscad_commands]
  else:
    logging.error("CPU count must be > 0.")
    results = []

  error_count += sum(1 for r in results if r != 0)

  # Summarize generation results
  end_time = support.get_process_time()
  if not args.no_summary:
    elapsed = support.get_duration(start_time, end_time)
    total_files = len(openscad_commands)
    logging.info(f"template_card.stl was {'regenerated' if should_regenerate_template else 'not regenerated'}.")
    logging.info(f"Generated {total_files} file{'s' if total_files != 1 else ''}.")
    logging.info(f"Elapsed time: {elapsed}")
    if error_count == 0 and warning_count == 0:
      logging.info("Generation completed successfully.")
    if error_count > 0:
      logging.error(f"Errors: {error_count}")
    if warning_count > 0:
      logging.warning(f"Warnings: {warning_count}")


def run_openscad_command(data: Data, progess: bool = False, progress_message: str | None = None):
  """Execute a single generation task.

  Args:
    data: Data object containing the OpenSCAD command and output metadata.
    progess: Whether to show progress feedback during execution.
    progress_message: Optional message to display while generating.

  Returns:
    The return code from the OpenSCAD subprocess.
  """
  logging.info(f"Generating [{str(data.count).rjust(len(str(data.total)), ' ')}/{data.total}]: {data.name.ljust(data.name_ljust, ' ')}  (./{str(data.rel_path).ljust(data.path_ljust, ' ')})")
  ret_code = support.subprocess_call(data.args, noexec=data.noexec, progress=progess, progress_message=progress_message)
  if ret_code != 0:
    logging.error(f"ERROR ({ret_code}) occurred while generating '{data.rel_path}'")
  return ret_code


def build_openscad_command_arguments(openscad_path: str, output_filepath: pathlib.Path, model_filepath: pathlib.Path, enable_textmetrics: bool = False, quiet: bool = False, *args: typing.Union[list[str], str]):
  """Build the OpenSCAD command-line arguments for a single export.

  Args:
    openscad_path: Path to the OpenSCAD executable.
    output_filepath: Destination STL path.
    model_filepath: Source SCAD model path.
    enable_textmetrics: Enable OpenSCAD textmetrics for text rendering.
    quiet: If True, pass OpenSCAD quiet mode flag.
    *args: Additional OpenSCAD arguments as strings or lists of strings.

  Returns:
    A list of OpenSCAD command-line arguments.
  """
  gen_args: list[str] = []
  gen_args.append(openscad_path)
  gen_args.extend(['-o', str(output_filepath)])
  gen_args.extend(['-o', str(output_filepath)])
  if enable_textmetrics:
    gen_args.extend(['--enable', 'textmetrics'])

  for a in args:
    if isinstance(a, str):
      gen_args.append(a)
    elif all(map(isinstance, a, itertools.repeat(str))):
      gen_args.extend(a)
    else:
      try:
        logging.error(f"Unexpected type of parameter: '{type(a)}': {a}")
      except:
        logging.error(f"Unexpected type of parameter: '{type(a)}': Unable to print variable value, str conversion failed.")

  if quiet:
    gen_args.append('-q')

  gen_args.append(str(model_filepath))
  return gen_args


def slugify(value: str, allow_unicode: bool = False):
  """Normalize a string into a filesystem-safe slug.

  Args:
    value: The input string to normalize.
    allow_unicode: If True, preserve unicode characters; otherwise convert to ASCII.

  Returns:
    A lowercase slug suitable for filenames and URLs.
  """
  value = str(value)
  if allow_unicode:
      value = unicodedata.normalize('NFKC', value)
  else:
      value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
  value = re.sub(r'[^\w\s-]', '', value.lower())
  return re.sub(r'[-\s]+', '-', value).strip('-_')


def get_relative_path(path: pathlib.Path) -> pathlib.Path:
  """Get the relative path of a file to cwd, simplified as much as possible.

  Args:
    path: The file path to simplify.

  Returns:
    The relative path if the file is within cwd, otherwise the absolute path.
  """
  try:
    return path.relative_to(cwd)
  except ValueError:
    # Path is not relative to cwd, return absolute
    return path


# Run the script
if __name__ == '__main__':
  try:
    main()
  except SystemExit as e:
    # SystemExit exception gets thrown on sys.exit() calls.
    # This has the exit code in the exception info.
    sys.exit(e.code)
  except KeyboardInterrupt:
    # Dont print exception info for KeyboardInterrupt exceptions (CTRL + C)
    # Keyboard interrputs default to a return value of 130, so return that.
    sys.exit(130)