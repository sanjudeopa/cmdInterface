# pylint: disable=missing-docstring

import sys
from os import walk, listdir

import yaml

class StatisticParser:
    GROUP_LIST = ("WRITE_GRP", "READ_GRP", "MACROS_GRP", "BARRIER_GRP",
                  "PRFM_GRP", "CP_OP_GRP", "INV_ALL_GRP", "D_CLEAN_INV_GRP",
                  "CP15_RD_GRP", "CP15_WR_GRP", "PWR_GRP", "L2_PARAM_GRP",
                  "NB_CAT_GEN")

    def __init__(self, stat_dir_path, summary_dir_path):
        self.stat_dir_path = stat_dir_path
        self.result_dict = {}
        self.prof_result_dict = {}
        self.stat_dict = {}
        self.summary_dir_path = summary_dir_path

    def read_yaml_stat_file(self, file_path):
        with open(file_path, "r") as file_in:
            generator = yaml.load(file_in).get("generator")
            if generator:
                self.stat_dict = generator

    def add_agents(self, grp_cat, key):
        if self.result_dict.get(grp_cat) is None:
            self.result_dict[grp_cat] = 0
        self.result_dict[grp_cat] += self.stat_dict[key[0]][key[1]]

    def normalize_results(self):
        for group in self.GROUP_LIST:
            self.result_dict[group+"_NORM"] = float(self.result_dict[group]) / self.result_dict["NB_CAT_GEN"] * 100

    @staticmethod
    def incr_clean_entry(key, result_dict):
        if result_dict.get(key) is None:
            result_dict[key] = 0
        result_dict[key] += 1

    def extract_measurement(self, group):
        return next((level
                     for (level, lo, hi) in (
                             ("", 0, 1),
                             ("{}_RESTRICTED".format(group), 1, 10),
                             ("{}_LOW".format(group), 10, 30),
                             ("{}_MEDIUM".format(group), 30, 60),
                     )
                     if lo <= self.result_dict["{}_NORM".format(group)] < hi
                    ),
                    "{}_MANY".format(group))


    def extract_profile(self):
        profile = ["PROF"]
        for key in [x for x in self.GROUP_LIST if x != "NB_CAT_GEN"]:
            profile.append(self.extract_measurement(key))
        prof_key = "_".join(profile)
        self.result_dict[prof_key] = 1
        self.incr_clean_entry(prof_key, self.prof_result_dict)

    def write_summary(self, summary_file):
        with open(summary_file, "w") as fh:
            for key in list(self.prof_result_dict):
                fh.write("{} {}\n".format(key, self.prof_result_dict[key]))

    def generate_test_profile(self):
        agent_l = list(self.stat_dict)
        key_l = []
        for agent in agent_l:
            key_l += [(agent, key) for key in self.stat_dict[agent]]
        print(key_l)
        for group in self.GROUP_LIST:
            for key in key_l:
                if key[1].find(group) != -1:
                    self.add_agents(group, key)
            if self.result_dict.get(group) is None:
                self.result_dict[group] = 0
        self.normalize_results()
        self.extract_profile()

    def clean_parsing_dir(self):
        self.result_dict = {}
        self.prof_result_dict = {}
        self.stat_dict = {}

    def generate_global_stat(self):
        directories_l = [direct[0] for direct in walk(self.stat_dir_path) if direct[0] != self.stat_dir_path]
        for direct in directories_l:
            file_name_l = listdir(direct)
            self.result_dict["TEST_CONFIG_NB"] = len(file_name_l)
            for fil in file_name_l:
                self.read_yaml_stat_file(direct+"/"+fil)
                self.generate_test_profile()
                self.stat_dict = {}
            self.write_summary(self.summary_dir_path + "/" + direct.split("/")[-1] + ".stats")
            self.clean_parsing_dir()

if __name__ == "__main__":
    stat_dir, summary_dir = sys.argv[1], sys.argv[2]
    stat_parser = StatisticParser(stat_dir, summary_dir)
    stat_parser.generate_global_stat()
