"""
A local database parameter storage implementation.
"""

import os
import base64
import getpass
import json
import sqlite3
import unicodedata
from typing import Optional, Union

from nacl import secret, pwhash, utils, hash as naclhash, encoding

from parci.internals.storage import SqliteKV
from parci import config
from parci.internals.utils import encode_bytes, decode_bytes

from .encrypt.password import get_user_decrypt_key, get_keys_by_password


def init():
    """
    Initialize the parameter storage database.
    """
    os.makedirs(os.path.dirname(config.PARAMETER_DB), mode=0o700, exist_ok=True)

    config_db = SqliteKV(db=config.PARAMETER_DB, table="config")
    if "password" in config_db:
        raise ValueError("Database already initialized")

    password1 = getpass.getpass()
    password2 = getpass.getpass("Password (again): ")

    if password1 != password2:
        raise ValueError("Passwords do not match")

    keysize = secret.SecretBox.KEY_SIZE
    salt = utils.random(pwhash.argon2id.SALTBYTES)
    opslimit = pwhash.argon2id.OPSLIMIT_SENSITIVE
    memlimit = pwhash.argon2id.MEMLIMIT_SENSITIVE
    key = get_user_decrypt_key(
        unicodedata.normalize("NFKC", password1).encode("utf-8"),
        salt,
        keysize=keysize,
        opslimit=opslimit,
        memlimit=memlimit,
    )
    box = secret.SecretBox(key)

    params_name_key = utils.random(keysize)
    params_name_nonce = utils.random(secret.SecretBox.NONCE_SIZE)
    params_value_key = utils.random(keysize)
    params_value_nonce = utils.random(secret.SecretBox.NONCE_SIZE)

    enc_name_key = box.encrypt(params_name_key, params_name_nonce)
    enc_value_key = box.encrypt(params_value_key, params_value_nonce)

    config_db["password"] = {
        "salt": encode_bytes(salt),
        "keysize": keysize,
        "opslimit": opslimit,
        "memlimit": memlimit,
        "name_key": encode_bytes(enc_name_key),
        "value_key": encode_bytes(enc_value_key),
    }

    config_db["default-open-method"] = "password"


def register_keyring():
    """
    Enable parameter database encryption using the system keyring.
    """
    # pylint: disable=import-outside-toplevel
    import keyring

    name_key, value_key = get_keys_by_password()
    key = utils.random(secret.SecretBox.KEY_SIZE)
    keystr = base64.b64encode(key).decode("ascii")

    box = secret.SecretBox(key)
    name_nonce = utils.random(secret.SecretBox.NONCE_SIZE)
    enc_name_key = box.encrypt(name_key, name_nonce)
    value_nonce = utils.random(secret.SecretBox.NONCE_SIZE)
    enc_value_key = box.encrypt(value_key, value_nonce)

    config_db = SqliteKV(db=config.PARAMETER_DB, table="config")
    config_db["keyring"] = {
        "name_key": encode_bytes(enc_name_key),
        "value_key": encode_bytes(enc_value_key),
    }

    keyring.set_password("parci", "parci", keystr)
    config_db["default-open-method"] = "keyring"


def get_keys_by_keyring():
    """
    Retrieve encryption keys from the system keyring.
    """
    # pylint: disable=import-outside-toplevel
    import keyring

    config_db = SqliteKV(db=config.PARAMETER_DB, table="config")
    kr_config = config_db["keyring"]
    for key in ("name_key", "value_key"):
        kr_config[key] = decode_bytes(kr_config[key])

    decrypt_keystr = keyring.get_password("parci", "parci")
    decrypt_key = base64.b64decode(decrypt_keystr)

    box = secret.SecretBox(decrypt_key)
    return box.decrypt(kr_config["name_key"]), box.decrypt(kr_config["value_key"])


class ParameterStore:
    """
    A local database-backed parameter store with encryption and decryption.
    """

    def __init__(
        self,
        db: Union[str, sqlite3.Connection],
        name_key: bytes,
        value_key: bytes,
        table: str = "params",
    ):
        self.kv = SqliteKV(db=db, table=table, serialize_values=False)
        self._name_key = name_key
        self._value_key = value_key

    def _calc_key(self, item):
        item = json.dumps(item).encode("utf-8")
        return naclhash.blake2b(
            item, key=self._name_key, encoder=encoding.HexEncoder
        ).decode("ascii")

    def __getitem__(self, item):
        db_key = self._calc_key(item)
        box = secret.SecretBox(self._value_key)
        value = self.kv[db_key]
        value = decode_bytes(value)
        value = box.decrypt(value)
        return json.loads(value)[1]

    def __setitem__(self, item, value):
        if config.PARAMETER_READ_ONLY:
            raise KeyError("ParameterStore is read-only")

        db_key = self._calc_key(item)
        box = secret.SecretBox(self._value_key)
        nonce = utils.random(secret.SecretBox.NONCE_SIZE)
        value = json.dumps([item, value]).encode("utf-8")
        value = box.encrypt(value, nonce)
        value = encode_bytes(value)
        self.kv[db_key] = value

    def __delitem__(self, item):
        if config.PARAMETER_READ_ONLY:
            raise KeyError("ParameterStore is read-only")

        db_key = self._calc_key(item)
        del self.kv[db_key]

    def __contains__(self, item):
        db_key = self._calc_key(item)
        return self.kv.__contains__(db_key)

    def items(self):
        """
        Return a list of (key, value) item pairs.
        """
        box = secret.SecretBox(self._value_key)

        for value in self.kv.values():
            value = decode_bytes(value)
            value = box.decrypt(value)
            k, v = json.loads(value)
            yield k, v

    def keys(self):
        """
        Return a list of all keys.
        """
        for k, _ in self.items():
            yield k

    def values(self):
        """
        Return a list of values stored in the ParameterStore.
        """
        for _, v in self.items():
            yield v

    def __iter__(self):
        return self.keys()


def open_parameter_store(method: Optional[str] = None):
    """
    Convenience function for opening a local parameter store.
    """
    config_db = SqliteKV(db=config.PARAMETER_DB, table="config")

    if method is None:
        method = config_db["default-open-method"]

    if method not in (
        "password",
        "yubikey",
        "keyring",
    ):
        raise ValueError('invalid encryption security method')

    if method == "password":
        name_key, value_key = get_keys_by_password(
            config.PARAMETER_DB_PASSWORD,
        )
    elif method == "yubikey":
        # pylint: disable=import-outside-toplevel
        from .encrypt.yubikey import get_keys_by_yubikey

        name_key, value_key = get_keys_by_yubikey()
    elif method == "keyring":
        name_key, value_key = get_keys_by_keyring()
    else:
        raise ValueError('method must be "password", "yubikey", or "keyring"')

    return ParameterStore(config.PARAMETER_DB, name_key, value_key)
