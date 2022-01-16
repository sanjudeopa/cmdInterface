from popeye_ml.project_specific import get_project_from_env_variable

import subprocess

import os
import logging
import pandas as pd
import shutil

import pathlib

from dory import ProjectInterface


class PopeyeDoryInterface(ProjectInterface):
    def __init__(self, clean_before_regress=False, bof=None, allowed_codes=list()):
        """
        Populate attributes needed by other methods.
        """
        self.project = get_project_from_env_variable()
        self.run_cmds = True
        self.clean_before_regress = clean_before_regress
        self.allowed_codes = allowed_codes
        if not bof:
            self.bof = "ml_bof.txt"
        else:
            self.bof = bof

    def generate_tests(self, num_tests, json_dir):
        """Use regress command to generate test candidates"""
        logging.info(
            "Generating Test Candidates. Number of tests = {}".format(num_tests)
        )
        cmd = []
        if self.clean_before_regress:
            cmd.append("blk_clean")
            cmd.append("--logs")
            cmd.append('generate_logs')
            cmd.append(";\n")
            # Delete previously dumped files
            output_dir = self.project.blk_val_execution_directory() / "ml_dump"
            # output_dir = json_dir
            if os.path.exists(output_dir) and os.path.isdir(output_dir):
                shutil.rmtree(output_dir)


        # blk_run cmd
        cmd.append("blk_run")
        cmd.append(f"--bof {self.project.build_options_list_file}")
        cmd.append("--build-clean")
        cmd.append(self.project.regression_list_file)
        cmd.append("--max-launch {}".format(num_tests))
        cmd.append("--ml-filter")
        cmd.append("--dfs simdir=local")
        cmd.append("--dfs keep=always")
        cmd.append("--no-sim")
        cmd.append("--path generate_logs")
        cmd.append('\necho "exxitcd $?"')
        logging.debug(cmd)
        if self.run_cmds:
            subprocess.Popen(cmd).wait()
            logging.info("Finished generating test candidates...")
        else:
            return " ".join(cmd)

    @staticmethod
    def _get_configs_from_command(cmd):
        cmd = cmd.split(" ")
        configs = []
        i = 0
        while i < len(cmd):
            token = cmd[i]
            if token == "blk_val":
                i += 1
                continue

            if token.startswith("-"):
                next_token = cmd[i + 1]
                if next_token.startswith("-"):
                    i += 1
                else:
                    i += 2
                continue

            return token

    def write_regress(self, tests, regress, build_out=None):
        """
        write a regression testlist to file.
        """
        logging.debug("Writing regression testlist...")

        regress_df = pd.DataFrame()
        build_df = pd.DataFrame()

        unique_builds_map = {}
        builds_list = []
        build_tags_list = []
        i = 0
        for build in tests.build_options.unique():
            unique_builds_map[build] = "build{}".format(i)
            builds_list.append(build.split(" ")[1])
            build_tags_list.append(unique_builds_map[build])
            i += 1

        build_df["build_options"] = builds_list
        build_df["tag"] = build_tags_list

        regress_df["config"] = tests.command.apply(
            lambda x: self.__class__._get_configs_from_command(x)
        )
        regress_df["seed"] = tests.seed
        regress_df["build"] = tests.build_options.apply(lambda x: unique_builds_map[x])

        regress_f = regress
        if not build_out:
            build_f = os.path.join(os.path.dirname(regress), "ml_bof.txt")
        else:
            build_f = build_out

        with open(regress_f, "w+") as fd:
            for row in regress_df.itertuples():
                line = "1 {} SEED={} TAGS={}\n".format(row.config, row.seed, row.build)
                fd.write(line)

        with open(build_f, "w+") as fd:
            for row in build_df.itertuples():
                line = "{} TAGS={}\n".format(row.build_options, row.tag)
                fd.write(line)

        return regress_f

    def regress(self, regression, num_tests=100, extra_args=list()):
        """
        Simulate filtered tests specified in testlist.
        """
        # blk_run --max-repeat 1 --max-launch (num of lines) [regress file] --build-options-file [bof] --mti --build
        cmd = list()
        regression = os.path.abspath(str(regression))
        bof = os.path.abspath(self.bof)
        if self.clean_before_regress:
            cmd.append("blk_clean")
            cmd.append("--logs")
            cmd.append("filtered_logs")
            cmd.append(";")

        # blk_run cmd
        cmd.append("blk_run")
        cmd.append("--max-repeat 1")
        cmd.append("--max-launch {}".format(num_tests))
        cmd.append("--bof {}".format(bof))
        cmd.append(regression)
        cmd.append("--path filtered_logs")
        cmd.append('--reg-tag MachineLearningApp_MLBugFinding_v0')
        cmd.extend(extra_args)
        # cmd.append(' --dfs simdir=local')
        # cmd.append(' --dfs keep=always')
        logging.debug(cmd)
        if self.run_cmds:
            subprocess.Popen(cmd).wait()
            logging.info("Finished running {0}.".format(cmd))
        else:
            return cmd

    def set_run_cmds(self, run_cmds):
        self.run_cmds = run_cmds

    def setup_project_env(self):
        cmds = list()
        cmds.append("#!/bin/csh\n")
        cmds.append("source /arm/tools/setup/init/tcsh\n")
        cmds.append("module load arm/cluster/2.0\n")
        cmds.append(f"cd {self.project.blk_val_execution_directory()}\n")
        cmds.append(f"{self.project.setuptb_command()}\n")
        return cmds

    def get_allowed_codes(self):
        return self.allowed_codes
