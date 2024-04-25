"""
Parci environment related functions.
"""

import os


class EnvAccessor:
    """
    A convenience accessor to environment variables.

    Instead of os.environ['SOME_VAR'], we can do env.SOME_VAR in parci taskfiles.
    """

    def __init__(self, **kwargs):
        self._old_envvars = {}
        for key, value in kwargs.items():
            self._old_envvars[key] = os.environ.get(key)
            os.environ[key] = value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for key, value in self._old_envvars.items():
            if value is None:
                os.environ.pop(key)
            else:
                os.environ[key] = value

    def __call__(self, **kwargs):
        return EnvAccessor(**kwargs)

    def __getattr__(self, name):
        return os.environ.get(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            os.environ[name] = value


env = EnvAccessor()
