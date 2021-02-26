"""Const for NiceHash integration."""

CONFIG_ENTRY_VERSION = 2
CONFIG_NAME = "name"
CONFIG_KEY = "key"
CONFIG_SECRET = "secret"
CONFIG_ORG_ID = "org_id"
CONFIG_FIAT = "fiat"
CONFIG_UPDATE_INTERVAL = "update_interval"

DOMAIN = "nicehash"
PLATFORMS = ["sensor"]
DEFAULT_SCAN_INTERVAL_MINUTES = 1
SWITCH_ASYNC_UPDATE_AFTER_SECONDS = 20

NICEHASH_API_ENDPOINT = "https://api2.nicehash.com"

SENSOR_DATA_COORDINATOR = "rig_sensor_coordinator"
API = "api"
UNSUB = "unsub"
SENSORS = "sensors"

ACCOUNT_OBJ = "account"
RIGS_OBJ = "rigs"

ALGOS_UNITS = {
    "SCRYPT": None,
    "SHA256": None,
    "SCRYPTNF": None,
    "X11": None,
    "X13": None,
    "KECCAK": None,
    "X15": None,
    "NIST5": None,
    "NEOSCRYPT": None,
    "LYRA2RE": None,
    "WHIRLPOOLX": None,
    "QUBIT": None,
    "QUARK": None,
    "AXIOM": None,
    "LYRA2REV2": None,
    "SCRYPTJANENF16": None,
    "BLAKE256R8": None,
    "BLAKE256R14": None,
    "BLAKE256R8VNL": None,
    "HODL": None,
    "DAGGERHASHIMOTO": "MH/s",
    "DECRED": None,
    "CRYPTONIGHT": None,
    "LBRY": None,
    "EQUIHASH": None,
    "PASCAL": None,
    "X11GOST": None,
    "SIA": None,
    "BLAKE2S": None,
    "SKUNK": None,
    "CRYPTONIGHTV7": None,
    "CRYPTONIGHTHEAVY": None,
    "LYRA2Z": None,
    "X16R": None,
    "CRYPTONIGHTV8": None,
    "SHA256ASICBOOST": None,
    "ZHASH": None,
    "BEAM": None,
    "GRINCUCKAROO29": "G/s",
    "GRINCUCKATOO31": "G/s",
    "LYRA2REV3": None,
    "CRYPTONIGHTR": None,
    "CUCKOOCYCLE": "G/s",
    "GRINCUCKAROOD29": "G/s",
    "BEAMV2": None,
    "X16RV2": None,
    "RANDOMXMONERO": "kH/s",
    "EAGLESONG": None,
    "CUCKAROOM": None,
    "GRINCUCKATOO32": "G/s",
    "HANDSHAKE": None,
    "KAWPOW": "MH/s",
    "CUCKAROO29BFC": None,
    "BEAMV3": None,
    "CUCKAROOZ29": None,
    "OCTOPUS": "MH/s",
}
