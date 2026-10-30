import os
import subprocess

import yaml

from zendev.proposal.repository import FrontmatterLoader


def fixtures(command: str, source: str) -> None:
    # ruleid: subprocess-shell
    subprocess.run(command, shell=True, check=True)
    # ruleid: subprocess-shell
    os.system(command)
    # ok: subprocess-shell
    subprocess.run(["git", "show", command], check=True)
    # ruleid: unsafe-yaml-loader
    yaml.load(source, Loader=yaml.Loader)
    # ruleid: unsafe-yaml-loader
    yaml.unsafe_load(source)
    # ok: unsafe-yaml-loader
    yaml.safe_load(source)
    # ok: unsafe-yaml-loader
    yaml.load(source, Loader=FrontmatterLoader)
