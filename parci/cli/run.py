"""
The run subcommand
"""

import parci
import parci.internals.task
from parci.internals.utils import (
    load_taskfile,
    get_starting_tasks,
    find_tasks,
    ready_tasks,
)
from parci.internals.docker import docker_cleanup


def run_tasks(args):
    """
    parci run entrypoint
    """
    taskfile = load_taskfile(args.taskfile)

    if args.start_at is None:
        starting_tasks = get_starting_tasks(taskfile)
    else:
        if args.start_at not in parci.internals.task.__all_tasks__:
            raise ValueError(f"No such task: {args.start_at!r}")
        starting_tasks = {parci.internals.task.__all_tasks__[args.start_at]}

    if not starting_tasks:
        raise ValueError("No starting tasks found")

    try:
        for starting_task in starting_tasks:
            # pylint: disable=no-member
            print(
                f"Starting execution at task: {taskfile.__file__} @ {starting_task}"
            )
            remaining_tasks = set()
            find_tasks({starting_task}, remaining_tasks)

            while remaining_tasks:
                ready = ready_tasks(remaining_tasks)
                if not ready and remaining_tasks:
                    raise ValueError(
                        f"No ready tasks and remaining tasks: {remaining_tasks}"
                    )
                for task in ready:
                    task.run(f"{taskfile.__file__} @ ")  # pylint: disable=no-member
                    remaining_tasks.remove(task)
            # pylint: disable=no-member
            print(
                f"Execution of starting taskset completed: {taskfile.__file__} @ {starting_task}"
            )
    finally:
        docker_cleanup()


def setup(parser):
    """
    parci run subcommand setup
    """
    parser.add_argument("taskfile", nargs="?", default="parci.taskfile")
    parser.add_argument("--start-at", help="Task to start execution at")
    parser.set_defaults(func=run_tasks)
