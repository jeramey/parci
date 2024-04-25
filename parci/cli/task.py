"""
parci task subcommand
"""

from parci.internals.utils import load_taskfile
from parci.internals.task import __all_tasks__ as all_tasks
from parci.internals.docker import docker_cleanup


def list_tasks(args):
    """
    parci task list implementation
    """
    taskfile = load_taskfile(args.taskfile)
    runme_task = None

    if hasattr(taskfile, "RUNME"):
        runme_task = taskfile.RUNME

    for key, value in all_tasks.items():
        if value is runme_task:
            print(f"{key} *")
        else:
            print(key)


def run_task(args):
    """
    parci task run implementation
    """
    taskfile = load_taskfile(args.taskfile)

    if args.task_name not in all_tasks:
        raise ValueError(f"Task {args.task_name} does not exist")

    try:
        this_task = all_tasks[args.task_name]
        return this_task.run(f"{taskfile.__file__} @ ")  # pylint: disable=no-member
    finally:
        docker_cleanup()


def setup(parser):
    """
    parci task subcommand setup
    """
    subp = parser.add_subparsers(metavar="COMMAND", required=True)

    list_p = subp.add_parser("list", help="List tasks")
    list_p.add_argument(
        "taskfile",
        nargs="?",
        default="parci.taskfile",
        help="Location of parci taskfile (default: parci.taskfile)",
    )
    list_p.set_defaults(func=list_tasks)

    run_p = subp.add_parser("run", help="Run a single task")
    run_p.add_argument("task_name", metavar="task-name", help="Task name to run")
    run_p.add_argument(
        "taskfile",
        nargs="?",
        default="parci.taskfile",
        help="Location of parci taskfile (default: parci.taskfile)",
    )
    run_p.set_defaults(func=run_task)
