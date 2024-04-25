"""
Parci task internals.
"""

__all_tasks__ = {}

import sys
from typing import Optional, Self


class TaskDagError(Exception):
    """Other task is already in the task DAG."""


class Task:
    """
    A parci Task object.
    """

    def __init__(self, name: Optional[str] = None):
        self._parents = set()
        self._children = set()
        self.has_run = False
        self.succeeded = None
        if name is None:
            self.name = self.__class__.__name__
        else:
            self.name = name

        if self.name in __all_tasks__:
            raise ValueError(f"Duplicate task found: {self.name}")

        __all_tasks__[self.name] = self

    @property
    def parents(self):
        """
        A list of the task's parents.
        """
        return tuple(self._parents)

    @property
    def children(self):
        """
        A list of tasks's children.
        """
        return tuple(self._children)

    def body(self):
        """
        Override this method to implement the body of a task.
        """
        raise NotImplementedError("Task.body is not implemented")

    def run(self, prefix="taskfile."):
        """
        Run the task.
        """
        print(f"Running task: {prefix}{self.name}")
        try:
            self.body()
            self.succeeded = True
        except Exception:
            print(f"ERROR: Task failed: {prefix}{self.name}", file=sys.stderr)
            self.succeeded = False
            raise
        finally:
            self.has_run = True

    @property
    def next_tasks(self):
        """
        A list of the next tasks in the DAG.
        """
        return tuple(self._children)

    def add_child_task(self, child: Self):
        """
        Adds a child task to the task DAG.
        """
        if not isinstance(child, Task):
            raise ValueError("Child must be a Task object")
        self._children.add(child)
        child.add_parent_task(self)

    def add_parent_task(self, parent: Self):
        """
        Add a parent task to the task DAG.
        """
        if not isinstance(parent, Task):
            raise ValueError("Parent must be a Task object")

        self._parents.add(parent)
        parent.add_child_task(self)

    def __lshift__(self, other: Self):
        self.add_child_task(other)

    def __rshift__(self, other: Self):
        self.add_parent_task(other)

    def __repr__(self):
        return f"<Task name={self.name!r}>"

    def __call__(self):
        return self.body()
