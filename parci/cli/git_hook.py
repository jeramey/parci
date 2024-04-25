"""
git-hook subcommand
"""

import io
import os
import subprocess
import tempfile
import zipfile

from parci import config
from parci.internals.storage import SqliteKV


def do_cmd(command) -> io.BytesIO:
    """
    Simple command runner that captures output.
    """
    c = subprocess.run(command, capture_output=True, check=True)
    return io.BytesIO(c.stdout)


def git_hook(args):
    """
    git-hook implementation.
    """
    if args.repository is None:
        raise ValueError("repository is required")

    db = SqliteKV(db=config.GIT_HOOK_STATE_DB, table=args.repository)

    branch_hashes = set()
    for line in do_cmd(["git", "ls-remote", args.repository]):
        line = line.decode("utf-8").strip()
        bhash, bname = line.split(None, 1)
        if bname == "HEAD":
            continue
        branch_hashes.add((bname, bhash))

    prev_branch_hashes = set(db.items())

    to_consider = branch_hashes - prev_branch_hashes

    # Update the database
    cur_names = {x[0] for x in branch_hashes}
    prev_names = {x[0] for x in prev_branch_hashes}
    rm_names = cur_names ^ prev_names
    for name in rm_names:
        del db[name]
    for bname, bhash in branch_hashes:
        db[bname] = bhash

    # Figure out if we should run parci tasks
    for bname, bhash in sorted(to_consider):
        try:
            zipdata = do_cmd(
                [
                    "git",
                    "archive",
                    "--format=zip",
                    "--remote",
                    args.repository,
                    bname,
                    "parci.taskfile",
                ]
            )
        except subprocess.CalledProcessError:
            print(f"Skipping {bname}: No parci.taskfile")
            continue

        try:
            # pylint: disable=consider-using-with
            zarch = zipfile.ZipFile(zipdata, mode="r")
            with tempfile.TemporaryDirectory(
                prefix="parci-" + bname.replace("/", "_") + "-"
            ) as tmpdir:
                zarch.extract("parci.taskfile", tmpdir)
                os.chdir(tmpdir)
                os.makedirs("work")
                os.chdir("work")
                print(f"Running parci for {bname} in {tmpdir}")
                os.environ["GIT_URL"] = args.repository
                if "refs/heads/" in bname:
                    os.environ["BRANCH_NAME"] = bname[len("refs/heads/") :]
                elif "refs/tags/" in bname:
                    os.environ["TAG_NAME"] = bname[len("refs/tags/") :]
                subprocess.run(["parci", "run", "../parci.taskfile"], check=True)
        except subprocess.CalledProcessError:
            print(f"Build for {bname} failed")
            continue
        finally:
            if "BRANCH_NAME" in os.environ:
                del os.environ["BRANCH_NAME"]
            if "TAG_NAME" in os.environ:
                del os.environ["TAG_NAME"]
            if "GIT_REPO" in os.environ:
                del os.environ["GIT_REPO"]


def setup(parser):
    """
    git-hook CLI setup
    """
    parser.add_argument("repository", nargs="?", default=os.environ.get("GIT_DIR"))
    parser.set_defaults(func=git_hook)
