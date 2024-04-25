"""
PARCI, a PARtial Continuous Integration tool
"""

import functools
import os
import shlex
import subprocess

from base64 import b64encode, b64decode
from typing import Union, Optional, Callable

from parci.internals.docker import docker_env
from parci.internals.docker import DockerContainer as docker
from parci.internals.docker import DockerNetwork as docker_net
from parci.internals.docker import DockerVolume as docker_vol
from parci.internals.environment import env
from parci.internals.parameter_store import params
from parci.internals.task import Task


def task(
    f: Union[Task, Callable[[], None]] = None, parent: Optional[Task] = None, **kwargs
):
    """
    A parci task decorator. Wraps a function to be executed by `parci run'.
    """

    def decorator(func):
        task_name = kwargs.get("name", getattr(func, "__name__", "UNKNOWN"))
        this_task = Task(name=task_name)
        this_task.body = func
        for key, value in kwargs.items():
            if not hasattr(this_task, key):
                raise ValueError(f"{key} is not a valid Task attribute")
            setattr(this_task, key, value)
        if parent is not None:
            parent.add_child_task(this_task)
        return this_task

    if isinstance(f, Task):
        return functools.partial(task, parent=f, **kwargs)

    if callable(f):
        return decorator(f)

    return decorator


##
# Useful utilities
##


def sh(command, shell="/bin/sh", check=True):
    """
    Execute a command string in a shell.
    """
    print("Exec:", " ".join([shlex.quote(x) for x in [shell, "-c", command]]))
    return subprocess.run([shell, "-c", command], check=check)


def cmd(command: Union[str, list, tuple], check=True):
    """
    Execute a basic command.
    """
    if isinstance(command, str):
        command = (command,)

    print("Exec:", " ".join([shlex.quote(x) for x in command]))
    return subprocess.run(command, check=check)


class chdir:
    # pylint: disable=invalid-name
    """
    A class for managing the current working directory in taskfiles.
    """

    def __init__(self, path):
        self._old_path = os.getcwd()
        os.chdir(path)
        self._thisdir = os.getcwd()

    def __enter__(self):
        os.chdir(self._thisdir)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self._old_path)

    def __truediv__(self, other: str):
        return chdir(other)

    def __str__(self):
        return os.getcwd()

    def __repr__(self):
        return f"<chdir {os.getcwd()}>"


def base64(data: Union[str, bytes]) -> Union[str, bytes]:
    """
    Encodes bytes to a base64 string, or decodes a base64 string to bytes.
    """
    if isinstance(data, str):
        return b64decode(data)
    if isinstance(data, bytes):
        return b64encode(data).decode("ascii")
    raise TypeError("Type of data is not str or bytes")


def cwd():
    """
    Returns the current working directory.
    """
    return chdir(".")


def mkdir(path, mode=0o777, exist_ok=True):
    """
    Create a directory, recursively if necessary.
    """
    return os.makedirs(str(path), mode, exist_ok)


workdir = chdir(os.getcwd())
uid = os.geteuid()
gid = os.getegid()


__all__ = (
    "task",
    "docker",
    "docker_net",
    "docker_vol",
    "docker_env",
    "workdir",
    "cwd",
    "chdir",
    "mkdir",
    "sh",
    "cmd",
    "params",
    "env",
    "uid",
    "gid",
    "base64",
)
