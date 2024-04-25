"""
Parci configuration.
"""

import os
import platform

DEBUG = os.environ.get("PARCI_DEBUG", False)
PARAMETER_DRIVER = os.environ.get("PARCI_PARAMETER_DRIVER", "local")

# Set the PARAMETER_DB location somewhat sensibly
if platform.system() == "Darwin":
    PARAMETER_DB = os.environ.get(
        "PARCI_PARAMETER_DB",
        os.path.join(os.path.expanduser("~"), "Library", "Parci", "params.db"),
    )
else:
    PARAMETER_DB = os.environ.get(
        "PARCI_PARAMETER_DB",
        os.path.join(
            os.environ.get(
                "XDG_DATA_HOME",
                os.path.join(os.path.expanduser("~"), ".local", "share"),
            ),
            "parci",
            "params.db",
        ),
    )


PARAMETER_DB_PASSWORD = os.environ.get("PARCI_PARAMETER_DB_PASSWORD", None)

PARAMETER_READ_ONLY = True

GIT_HOOK_STATE_DB = os.environ.get(
    "PARCI_GIT_HOOK_STATE_DB",
    os.path.join(os.path.dirname(PARAMETER_DB), "git-hook-state.db"),
)

# Clean the namespace up.
del os
del platform
