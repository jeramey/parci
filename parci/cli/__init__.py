"""
Parci Command Line Interface
"""

import argparse
import json
import sys
import traceback

from parci import config

from . import run, param, git_hook, task


def config_type(value: str):
    """
    Parse a --config command line parameter and update global config state
    """
    if "=" not in value:
        raise ValueError("Not a valid config key=value pair")
    key, value = value.split("=", 1)
    key = key.upper()
    key = key.replace("-", "_")

    if not hasattr(config, key):
        raise ValueError("Unknown config key")
    try:
        value = json.loads(value)
    except json.JSONDecodeError:
        pass

    setattr(config, key, value)
    return key, value


def main():
    """
    main entrypoint for CLI
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", "-c", type=config_type, action="append")
    parser.add_argument("--debug", action="store_true")
    # Set configuration which might be needed for sub-parser setups
    args, rest = parser.parse_known_args()

    if args.debug:
        config.DEBUG = True

    subparser = parser.add_subparsers(required=True, metavar="COMMAND")
    run.setup(subparser.add_parser("run", help="Run parci.taskfile tasks"))
    param.setup(subparser.add_parser("param", help="Modify tasklist parameters"))
    git_hook.setup(subparser.add_parser("git-hook", help="Run the git hook"))
    task.setup(subparser.add_parser("task", help="Task management"))

    parser.add_argument("--help", "-h", action="help")

    rargs = parser.parse_args(rest)
    try:
        rargs.func(rargs)
    except Exception as e:  # pylint: disable=broad-exception-caught
        if config.DEBUG:
            print(traceback.format_exc(), file=sys.stderr)
        else:
            parser.error(message=str(e))
