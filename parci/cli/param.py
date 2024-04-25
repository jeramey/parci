"""
parci param subcommand CLI implementation.
"""

import json
import sys
import traceback

import parci

from parci import config
from parci.internals.parameter_store.local import init, register_keyring


def local_init(_args):
    """
    param init implementation
    """

    init()


def local_register_yubikey(args):
    """
    param register-yubikey implementation
    """
    # pylint: disable=import-outside-toplevel
    from parci.internals.parameter_store.local.encrypt.yubikey import (
        register_yubikey,
        SLOT,
    )

    register_yubikey(SLOT(args.slot))


def local_register_keyring(_args):
    """
    param register-keyring implementation
    """
    register_keyring()


def set_param(args):
    """
    param set implementation
    """
    config.PARAMETER_READ_ONLY = False
    if args.value is None or args.value == "-":
        if sys.stdin.isatty():
            print("Tell me your secrets (type ^D when done)...", file=sys.stderr)
        secret = sys.stdin.read()
    else:
        secret = args.value

    if args.json:
        secret = json.loads(secret)

    parci.params[args.name] = secret


def list_params(_args):
    """
    param list implementation
    """
    for key in parci.params.keys():
        print(key)


def get_param(args):
    """
    param get implementation
    """
    print(repr(parci.params[args.name]))


def rm_param(args):
    """
    param rm implementation
    """
    config.PARAMETER_READ_ONLY = False

    del parci.params[args.name]


def setup(parser):
    """
    param subcommand CLI setup
    """
    subparsers = parser.add_subparsers(metavar="COMMAND", required=True)
    if config.PARAMETER_DRIVER == "local":
        init_p = subparsers.add_parser(
            "init", help="Initialize the local parameter database"
        )
        init_p.set_defaults(func=local_init)

        kr_p = subparsers.add_parser(
            "register-keyring", help="Register encryption keys in the OS keyring"
        )
        kr_p.set_defaults(func=local_register_keyring)

        try:
            # pylint: disable=import-outside-toplevel
            from yubikit.yubiotp import SLOT

            yk_p = subparsers.add_parser(
                "register-yubikey", help="Register encryption with a Yubikey"
            )
            yk_p.add_argument("--slot", type=SLOT, default=SLOT(2))
            yk_p.set_defaults(func=local_register_yubikey)
        except ImportError:
            if config.DEBUG:
                traceback.print_exc()

    list_p = subparsers.add_parser("list", help="List available parameters")
    list_p.set_defaults(func=list_params)

    get_p = subparsers.add_parser("get", help="Get a specific parameter")
    get_p.add_argument("name")
    get_p.set_defaults(func=get_param)

    set_p = subparsers.add_parser("set", help="Set a parameter")
    set_p.add_argument("name")
    set_p.add_argument("value", nargs="?", default=None)
    set_p.add_argument(
        "--json", action="store_true", help="Parse given secret as JSON before storing"
    )
    set_p.set_defaults(func=set_param)

    rm_p = subparsers.add_parser("rm", help="Remove a parameter")
    rm_p.add_argument("name")
    rm_p.set_defaults(func=rm_param)
