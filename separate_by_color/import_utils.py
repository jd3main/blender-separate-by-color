import os
import sys
import ensurepip
import subprocess
import importlib
from collections import namedtuple


Dependency = namedtuple("Dependency", ["package", "module_name", "global_name"])


def import_dependencies(dependencies, global_vars):
    ensure_pip()
    if dependencies is None:
        raise ValueError('dependencies should not be None')
    if  global_vars is None:
        raise ValueError('global_vars should not be None')
    for dependency in dependencies:
        install_and_import(*dependency, global_vars)


_pip_ensured = False
def ensure_pip():
    global _pip_ensured
    if not _pip_ensured:
        _pip_ensured = True
        ensurepip.bootstrap()
        os.environ.pop("PIP_REQ_TRACKER", None)

def install_and_import(package_name, module_name, global_name, global_vars):
    install_package(package_name)
    import_module(module_name, global_name, global_vars)


def install_package(package_name):
    python = sys.executable
    output = subprocess.check_output([python, '-m', 'pip', 'install', package_name])
    print(output)


def import_module(module_name, global_name, global_vars):
    global_vars[global_name] = importlib.import_module(module_name)
