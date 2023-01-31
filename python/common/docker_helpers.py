#  31.01.2023 ----------------------------------------------------------------------------------------------------------------------
#  created by: Felix Eickeler
#              felix.eickeler@tum.de
# ----------------------------------------------------------------------------------------------------------------------------------

from pathlib import Path, PurePath
import subprocess
from subprocess import PIPE
import os

TLS_HOST = False
DOCKER_PATH = Path(__file__).parent.parent.parent / "docker"

def docker_run(dstring):
    env = os.environ.copy()
    if TLS_HOST:
        env["DOCKER_HOST"] = "tcp://127.0.0.1:2376"
        env["DOCKER_TLS_VERIFY"] = "1"
    subprocess.run(dstring, cwd=DOCKER_PATH, env=env)


def create_docker(input_path, output_path, docker_name: str):
    if not (DOCKER_PATH / "docker-compose.yml").exists():
        raise f"Docker-Compose file could not be found @ {DOCKER_PATH}"
    env = os.environ.copy()
    # depended on os
    from sys import platform
    if platform != "win32":
        env["UUID"] = os.getuid().__str__()
        env["GID"] = os.getgid().__str__()
    env["SRC"] = input_path.__str__()
    env["DST"] = output_path.__str__()
    env["PWD"] = DOCKER_PATH.__str__()
    # These commands are if tls is enabled.
    dstring = ['docker-compose', 'up', "--no-start", "--force", docker_name]  # ], "tail", "-f", "/dev/null"]

    create = subprocess.run(dstring, cwd=DOCKER_PATH, env=env)
    if create.returncode != 0:
        env["DOCKER_HOST"] = "tcp://127.0.0.1:2376"
        env["DOCKER_TLS_VERIFY"] = "1"
        global TLS_HOST
        TLS_HOST = True
        print(f'Switching to TLS configuration: DOCKER_HOST = {env["DOCKER_HOST"]}; DOCKER_TLS_VERIFY {env["DOCKER_TLS_VERIFY"]}')
        create = subprocess.run(dstring, cwd=DOCKER_PATH, env=env)
        if create.returncode != 0:
            raise RuntimeError("Docker container could not be created or build")
    dstring = ['docker-compose', 'start', docker_name]
    return subprocess.run(dstring, cwd=DOCKER_PATH, env=env)
