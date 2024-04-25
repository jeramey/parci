"""
Yubikey-based storage encryption.
"""

import ykman.device
from nacl import secret, pwhash, utils
from ykman.base import YkmanDevice
from yubikit.core.otp import OtpConnection
from yubikit.yubiotp import SLOT, YubiOtpSession

from parci import config
from parci.internals.utils import encode_bytes, decode_bytes
from parci.internals.storage import SqliteKV

from .password import get_keys_by_password


def get_yubikey_decrypt_key(
    device: YkmanDevice,
    slot: SLOT,
    challenge: bytes,
    salt: bytes,
    keysize=secret.SecretBox.KEY_SIZE,
    opslimit=pwhash.argon2id.OPSLIMIT_SENSITIVE,
    memlimit=pwhash.argon2id.MEMLIMIT_SENSITIVE,
):
    """
    Get a derived key from a Yubikey device.
    """
    connection = device.open_connection(OtpConnection)
    session = YubiOtpSession(connection)
    response = session.calculate_hmac_sha1(slot, challenge)
    return pwhash.argon2id.kdf(
        keysize, response, salt, opslimit=opslimit, memlimit=memlimit
    )


def register_yubikey(slot: SLOT = SLOT(2)):
    """
    Register first YubiKey found using OTP challenge response slot given.
    """
    # pylint: disable=too-many-locals

    name_key, value_key = get_keys_by_password()

    device, info = ykman.device.list_all_devices()[0]
    serial = info.serial
    challenge = utils.random(64)
    salt = utils.random(pwhash.argon2id.SALTBYTES)
    keysize = secret.SecretBox.KEY_SIZE
    opslimit = pwhash.argon2id.OPSLIMIT_SENSITIVE
    memlimit = pwhash.argon2id.MEMLIMIT_SENSITIVE

    key = get_yubikey_decrypt_key(
        device=device,
        slot=slot,
        challenge=challenge,
        salt=salt,
        keysize=keysize,
        opslimit=opslimit,
        memlimit=memlimit,
    )
    name_nonce = utils.random(secret.SecretBox.NONCE_SIZE)
    value_nonce = utils.random(secret.SecretBox.NONCE_SIZE)

    box = secret.SecretBox(key)

    enc_name_key = box.encrypt(name_key, name_nonce)
    enc_value_key = box.encrypt(value_key, value_nonce)

    config_db = SqliteKV(db=config.PARAMETER_DB, table="config")
    # pylint: disable=duplicate-code
    config_db[f"yubikey:{serial}"] = {
        "slot": slot.value,
        "challenge": encode_bytes(challenge),
        "salt": encode_bytes(salt),
        "keysize": keysize,
        "opslimit": opslimit,
        "memlimit": memlimit,
        "name_key": encode_bytes(enc_name_key),
        "value_key": encode_bytes(enc_value_key),
    }
    config_db["default-open-method"] = "yubikey"


def get_keys_by_yubikey():
    """
    Retrieve encryption keys from a registered Yubikey.
    """
    config_db = SqliteKV(db=config.PARAMETER_DB, table="config")
    device, info = ykman.device.list_all_devices()[0]
    serial = info.serial
    yk_config = config_db[f"yubikey:{serial}"]
    for key in ("challenge", "salt", "name_key", "value_key"):
        yk_config[key] = decode_bytes(yk_config[key])

    decrypt_key = get_yubikey_decrypt_key(
        device=device,
        slot=SLOT(yk_config["slot"]),
        challenge=yk_config["challenge"],
        salt=yk_config["salt"],
        keysize=yk_config["keysize"],
        opslimit=yk_config["opslimit"],
        memlimit=yk_config["memlimit"],
    )
    box = secret.SecretBox(decrypt_key)
    return box.decrypt(yk_config["name_key"]), box.decrypt(yk_config["value_key"])
