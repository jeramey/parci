"""
Password-based storage encryption.
"""

import getpass
import unicodedata
from typing import Optional

from nacl import secret, pwhash

from parci import config
from parci.internals.utils import decode_bytes
from parci.internals.storage import SqliteKV


def get_user_decrypt_key(
    password: bytes,
    salt: bytes,
    keysize=secret.SecretBox.KEY_SIZE,
    opslimit=pwhash.argon2id.OPSLIMIT_SENSITIVE,
    memlimit=pwhash.argon2id.MEMLIMIT_SENSITIVE,
):
    """
    Get a derived key from a password and salt.
    """
    return pwhash.argon2id.kdf(
        keysize, password, salt, opslimit=opslimit, memlimit=memlimit
    )


def get_keys_by_password(password: Optional[str] = None):
    """
    Retrieve encryption keys via the password provided.
    """
    config_db = SqliteKV(db=config.PARAMETER_DB, table="config")
    password_config = config_db["password"]
    for key in ("salt", "name_key", "value_key"):
        password_config[key] = decode_bytes(password_config[key])

    if password is None:
        password = getpass.getpass()

    decrypt_key = get_user_decrypt_key(
        password=unicodedata.normalize("NFKC", password).encode("utf-8"),
        salt=password_config["salt"],
        keysize=password_config["keysize"],
        opslimit=password_config["opslimit"],
        memlimit=password_config["memlimit"],
    )
    box = secret.SecretBox(decrypt_key)
    return box.decrypt(password_config["name_key"]), box.decrypt(
        password_config["value_key"]
    )
