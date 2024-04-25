"""
Miscellaneous utility functions that don't obviously belong anywhere else.
"""

import base64
import types
from typing import Iterable, Set

from parci.internals.task import Task


def encode_bytes(b: bytes):
    """
    Helper function to encode a bytes object to a string.
    """
    return base64.b64encode(b).decode("ascii")


def decode_bytes(s: str):
    """
    Helper function to decode a string to a bytes object.
    """
    return base64.b64decode(s)


def load_taskfile(filename: str) -> types.ModuleType:
    """
    Load a parci.taskfile and compile it.
    """
    with open(filename, "r", encoding="utf-8") as fobj:
        taskfile = types.ModuleType("taskfile")
        taskfile.__file__ = filename
        compiled = compile(fobj.read(), filename, "exec")
        # exec() is intentional here
        # pylint: disable=exec-used
        exec(compiled, taskfile.__dict__)  # nosec B102
        return taskfile


def get_starting_tasks(taskfile: types.ModuleType) -> Iterable[Task]:
    """
    Locate the first task that should be run in a taskfile.
    """
    if hasattr(taskfile, "RUNME"):
        if isinstance(taskfile.RUNME, Task):
            return [taskfile.RUNME]
        if isinstance(taskfile.RUNME, Iterable) and all(
            isinstance(x, Task) for x in taskfile.RUNME
        ):
            return taskfile.RUNME
    raise ValueError(f"{taskfile.__file__} has no RUNME tasks")


def find_tasks(taskset: Set[Task], recordset: Set[Task]):
    """
    Find all of the tasks in a task sequence.
    """
    for task in taskset:
        recordset.add(task)
        for child in task.children:
            if child in recordset:  # Break cycles
                continue
            find_tasks({child}, recordset)


def ready_tasks(taskset: Set[Task]) -> Set[Task]:
    """
    Get a list of tasks which are ready to be run.
    """
    ready = set()
    for task in taskset:
        if task.has_run:
            continue

        if all(parent.has_run and parent.succeeded for parent in task.parents):
            ready.add(task)

    return ready
