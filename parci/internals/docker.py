"""
Docker container, network, and volume management for parci.
"""

import shlex
import subprocess
import tempfile
import uuid

from base64 import b32encode

from parci.constants import workdir as startup_workdir, uid, gid

_docker_networks = set()
_docker_volumes = set()
_docker_containers = set()


def docker_cleanup():
    """
    Clean up all spawned docker containers, networks, and volumes.
    """
    for container in list(_docker_containers):
        container.cleanup()
    for volume in list(_docker_volumes):
        volume.cleanup()
    for network in list(_docker_networks):
        network.cleanup()


def _parci_id(prefix="parci"):
    """
    Generate a unique id for docker objects.
    """
    return prefix + "-" + b32encode(uuid.uuid4().bytes).decode("ascii").replace("=", "")


class DockerNetwork:
    """
    A convenience class for managing docker networks in parci taskfiles.
    """

    def __init__(self):
        self.network_name = _parci_id("parci-net")
        subprocess.run(["docker", "network", "create", self.network_name], check=True)
        _docker_networks.add(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any([exc_type, exc_val, exc_tb]):
            # Delay cleanup
            return
        self.cleanup()

    def cleanup(self):
        """
        Clean up after myself.
        """
        print(f"Cleaning up network {self.network_name}")
        subprocess.run(
            ["docker", "network", "remove", self.network_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        _docker_networks.remove(self)


class DockerVolume:
    """
    A convenience class for managing docker volumes in parci taskfiles.
    """

    def __init__(self):
        self.volume_name = _parci_id("parci-vol")
        subprocess.run(["docker", "volume", "create", self.volume_name], check=True)
        _docker_volumes.add(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any([exc_type, exc_val, exc_tb]):
            # Delay cleanup
            return
        self.cleanup()

    def cleanup(self):
        """
        Clean up after myself.
        """
        print(f"Cleaning up volume {self.volume_name}")
        subprocess.run(
            ["docker", "volume", "remove", self.volume_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        _docker_volumes.remove(self)


class DockerContainer:
    """
    A convenience class for managing docker containers in parci taskfiles.
    """

    # pylint: disable=too-many-arguments,too-many-locals
    def __init__(
        self,
        image_name,
        command=(),
        entrypoint=None,
        network=None,
        name=None,
        env=None,
        workdir=None,
        volumes=None,
        user=None,
        privileged=False,
        detach=False,
        tty=False,
        interactive=False,
    ):
        self.container_name = _parci_id("parci-ctnr")
        docker_args = ["docker", "container", "run", f"--name={self.container_name}"]

        if detach:
            docker_args.append("--detach")

        if privileged:
            docker_args.append("--privileged")

        if tty:
            docker_args.append("--tty")

        if interactive:
            docker_args.append("--interactive")

        # pylint: disable=consider-using-with
        envfile = tempfile.NamedTemporaryFile(mode="w")
        if hasattr(env, "items"):
            for key, value in env.items():
                envfile.write(f"{key}={value}\n")
        elif env is not None:
            envfile.write(env)
        envfile.flush()
        docker_args.append(f"--env-file={envfile.name}")

        if name is not None:
            docker_args.append(f"--network-alias={name}")

        if entrypoint is not None:
            docker_args.append(f"--entrypoint={entrypoint}")

        if workdir is not None:
            docker_args.append(f"--workdir={workdir}")

        if isinstance(volumes, str):
            docker_args.append("--volume=" + volumes)
        elif hasattr(volumes, "items"):
            for key, value in volumes.items():
                if isinstance(key, DockerVolume):
                    docker_args.append(f"--volume={key.volume_name}:{value}")
                else:
                    docker_args.append(f"--volume={key}:{value}")

        if network is not None:
            if isinstance(network, DockerNetwork):
                docker_args.append(f"--network={network.network_name}")
            else:
                docker_args.append(f"--network={network}")

        if user is not None:
            docker_args.append(f"--user={user}")

        docker_args.append(image_name)

        if isinstance(command, str):
            docker_args.append(command)
        elif command:
            docker_args.extend(list(command))

        print("Exec:", " ".join([shlex.quote(x) for x in docker_args]))
        try:
            subprocess.run(docker_args, check=True)
        finally:
            _docker_containers.add(self)
            envfile.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if any([exc_type, exc_val, exc_tb]):
            # Delay cleanup
            return
        self.cleanup()

    def stop(self, check=True):
        """
        Stop this container.
        """
        subprocess.run(
            ["docker", "container", "stop", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=check,
        )

    def start(self):
        """
        Start this container.
        """
        subprocess.run(
            ["docker", "container", "start", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    def wait(self, check=True):
        """
        Wait for a container to exit.
        """
        subprocess.run(
            ["docker", "container", "wait", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=check,
        )

    def attach(self):
        """
        Attach to this container, resuming execution only after it has finished.
        """
        subprocess.run(
            ["docker", "container", "attach", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )

    def remove(self, check=True):
        """
        Remove this container.
        """
        subprocess.run(
            ["docker", "container", "rm", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=check,
        )

    def exec(
        self,
        command,
        detach=False,
        env=None,
        privileged=False,
        interactive=False,
        tty=False,
        user=None,
        workdir=None,
        shell=False,
    ):
        """
        Execute a command inside this container.
        """

        docker_args = ["docker", "container", "exec"]

        if detach:
            docker_args.append("--detach")
        if privileged:
            docker_args.append("--privileged")
        if interactive:
            docker_args.append("--interactive")
        if tty:
            docker_args.append("--tty")
        if user is not None:
            docker_args.append(f"--user={user}")
        if workdir is not None:
            docker_args.append(f"--workdir={workdir}")

        envfile = None
        if env is not None:
            # pylint: disable=consider-using-with
            envfile = tempfile.NamedTemporaryFile(mode="w")
            if hasattr(envfile, "items"):
                for key, value in env.items():
                    envfile.write(f"{key}={value}\n")
            else:
                envfile.write(env)
            envfile.flush()
            docker_args.append(f"--env-file={envfile.name}")

        docker_args.append(self.container_name)
        if isinstance(shell, str):
            docker_args.extend([shell, "-c", command])
        elif shell is True:
            docker_args.extend(["/bin/sh", "-c", command])
        elif isinstance(command, str):
            docker_args.append(command)
        else:
            docker_args.extend(command)

        try:
            print("Exec:", " ".join([shlex.quote(x) for x in docker_args]))
            subprocess.run(docker_args, check=True)
        finally:
            if envfile is not None:
                envfile.close()

    def cleanup(self):
        """
        Clean up after myself.
        """
        print(f"Cleaning up container: {self.container_name}")
        self.stop(check=False)
        self.wait(check=False)
        self.remove(check=False)
        _docker_containers.remove(self)


def docker_env(image_name, **kwargs):
    """
    Create a new temporary Docker environment running in the background with the workspace
    mounted and running as the uid and gid we are currently running as.

    Doing this requires that the image name given has /bin/sh available.
    """
    kwargs["entrypoint"] = "/bin/sh"
    kwargs["command"] = ["-c", "bye () { exit 0; };  trap bye TERM; read BLAH"]
    kwargs["interactive"] = True
    kwargs["detach"] = True
    kwargs["user"] = f"{uid}:{gid}"
    kwargs["workdir"] = startup_workdir
    if "volumes" in kwargs:
        if isinstance(kwargs["volumes"], str):
            name, value = kwargs["volumes"].split(":", 1)
            kwargs["volumes"] = {name: value}
        elif not isinstance(kwargs["volumes"], dict):
            raise ValueError("Weird volume type")
    else:
        kwargs["volumes"] = {}
    kwargs["volumes"][startup_workdir] = startup_workdir

    return DockerContainer(image_name=image_name, **kwargs)
