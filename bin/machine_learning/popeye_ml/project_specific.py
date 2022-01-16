#!/usr/bin/env python

import os
import pathlib
import sys


class MlUnkownProjectError(Exception):
    """Raised when the project is not supported by ML"""


class MlUnkownEnvVariableError(Exception):
    """Raised when the a mandatory env variable does not exists"""


class MlProject:
    "Stores project specific information"
    def __init__(self, name: str, eap_name: str, lsf_project_code: str, project_directory: str, build_options_list_file: str, regression_list_file: str):
        self.name = name
        self.eap_name = eap_name
        self.lsf_project_code = lsf_project_code
        self.project_directory = project_directory
        self.build_options_list_file = build_options_list_file
        self.regression_list_file = regression_list_file

    @staticmethod
    def blk_val_execution_directory() -> pathlib.Path:
        "Directory in which blkval commands must be executed"
        return pathlib.Path(__file__).parents[3]

    @staticmethod
    def setuptb_command() -> str:
        "Command to source blkval environement"
        return "source setupTB --force\n"


class SophiaMlProject(MlProject):
    "Stores project specific information for Sophia CPU projects"

    @staticmethod
    def blk_val_execution_directory() -> pathlib.Path:
        return pathlib.Path(__file__).parents[5].joinpath(pathlib.Path("/simulation/memsys_tb"))

    @staticmethod
    def setuptb_command() -> str:
        return "source setupTB -nf\n"


ML_PROJECT_LIST = {
        "makalu":
        MlProject(name="makalu",
                  eap_name="makalu",
                  lsf_project_code="PJ02794",
                  project_directory="pj02794_matterhorn",
                  build_options_list_file="build_configs/makalu_reference.txt",
                  regression_list_file="regression/popeye/default_makalu.list"),
        "hunter":
        SophiaMlProject(name="hunter",
                        eap_name="yeti",
                        lsf_project_code="PJ33000021",
                        project_directory="yeti_pj33000021/dev/popeye",
                        build_options_list_file="reference.txt",
                        regression_list_file="regression/popeye/default_makalu.list"),
        "klein":
        MlProject(name="klein",
                  eap_name="klein",
                  lsf_project_code="PJ02607C",
                  project_directory="pj02607_klein",
                  build_options_list_file="klein/simulation/popeye/build_configs/klein.r1.all.txt",
                  regression_list_file="klein/simulation/popeye/regression/klein.quick.list"),

        "hayes":
        MlProject(name="hayes",
                  eap_name="hayes",
                  lsf_project_code="PJ1000662",
                  project_directory="hayes_pj1000662",
                  build_options_list_file="hayes/simulation/popeye/build_configs/hayes.all.txt",
                  regression_list_file="hayes/simulation/popeye/regression/hayes.quick.list",
    ),
}


def is_valid_project(project: str) -> bool:
    """
    Returns True if the project is valid
    """
    return project in ML_PROJECT_LIST


def get_project_from_env_variable() -> MlProject:
    """
    Returns project from environment variable (setupTB needs to be sources)
    """
    project = os.environ.get('ML_PROJECT_NAME', None)
    if not project:
        raise MlUnkownEnvVariableError("Environment variable ML_PROJECT_NAME is not set. Please set it manually or with setupTB script.")
    return get_project_from_name(project)


def get_project_from_name(project_name: str) -> MlProject:
    if not is_valid_project(project_name):
        raise MlUnkownProjectError(f"This project {project_name} is not valid for ML work")
    return ML_PROJECT_LIST[project_name]


if __name__ == "__main__":
    print(get_project_from_env_variable().lsf_project_code)
    sys.exit(0)
