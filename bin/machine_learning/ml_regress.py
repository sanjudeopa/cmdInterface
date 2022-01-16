#!/usr/bin/env python3

import argparse

from popeye_ml.project_specific import get_project_from_env_variable
import pathlib
import os
import json
import glob
from datetime import datetime, timedelta
from typing import List, Dict, ByteString, Optional
import ast
import zlib

import pandas as pd
import joblib

from distributed import Client, worker_client

import prefect
from prefect import task, Flow
from prefect.core.task import Task
from prefect.utilities.debug import raise_on_exception
from prefect.engine.flow_runner import FlowRunner

import dory
from dory.jobqueue import start_cluster, make_executor
from dory.lifecycle.model_store.local import LocalModelStore
from dory.flows.bug_discovery import BugDiscoveryFlow
from dory.flows.preprocessing.bug_discovery import PopeyePreprocessing
import dory.tasks as dt
from dory.util import flatten_dict
from dory.datastore_interface.eap_s3 import EAPInterfaceS3

from popeye_ml.popeye_dory_interface import PopeyeDoryInterface

logger = dory.utilities.logging.configure_logging()

def parse_args():
    """parse cli args"""
    parser = argparse.ArgumentParser(
        description="Test script for bug discovery integration.",
        epilog="""
        """,
    )

    # Positional args
    parser.add_argument("application", help="application profile to run.")

    # Options
    parser.add_argument(
        "--num-tests", help="Number of tests to run.", type=int, default=500
    )
    # Options
    parser.add_argument(
        "--num-generate",
        help="Number of candidates to generate.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--model-prefix", help="Model prefix, for testing.",
        default=None,
        type=str
    )
    parser.add_argument(
        "--output", help="Where to put output artifacts.",
        default="./ml_regress",
        type=str
    )

    parser.add_argument(
        "--training-subsample",
        help="During integration testing we may want to subsample training data so things go fast."
        "Number of rows to sample.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--candidate-csv",
        help="CSV from which to load test candidates.",
        default=None,
        type=str
    )
    parser.add_argument(
        "--training-csv",
        help="CSV from which to load training data.",
        default=None,
        type=str
    )
    parser.add_argument(
        "--fetch-train-data",
        help="Fetches train data from EAP for training.",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--fetch-train-from-date",
        help=(
            "Start of date range for fetching train data from EAP. Given as <year><month><date>"
            "eg. 20210110 for jan 10th 2021"
        ),
        default=(datetime.today().date() - timedelta(days=14)).strftime("%Y%m%d"),
    )
    parser.add_argument(
        "--fetch-train-to-date",
        help=(
            "End of date range for fetching train data from EAP. given as <year><month><date>"
            "eg. 20210110 for jan 10th 2021"
        ),
        default=datetime.today().date().strftime("%Y%m%d"),
    )
    parser.add_argument(
        "--fetch-train-usertag",
        help='user tags to filter EAP data on.',
        default="[\"ML_UPLOAD\",]",
    )
    parser.add_argument(
        "--fetch-train-output",
        help="file to output dataset to. defaults to a file in current directory",
        default=None,
        type=str
    )

    dask_grp = parser.add_argument_group("dask options", "control dask resource usage")
    dask_grp.add_argument(
        "--max-workers",
        help="Maximum workers for the distributed dask cluster.",
        type=int,
        default=8,
    )
    dask_grp.add_argument(
        "--min-workers",
        help="Minimum workers for the distributed dask cluster.",
        type=int,
        default=1,
    )
    dask_grp.add_argument(
        "--dask-memory",
        help="Memory size in gigabytes for the distributed dask cluster.",
        type=int,
        default=10,
    )

    # Flags
    flags = parser.add_argument_group("flags", "flow control flags")

    flags.add_argument(
        "--dry-run",
        help="Only show what would be done, don't actually do anything.",
        action="store_true",
        default=False,
    )
    flags.add_argument(
        "--date-as-sid",
        help="Workaround. Replace SID with Date. For flow testing only.",
        action="store_true",
        default=False,
    )
    flags.add_argument(
        "--no-run",
        help="Do not run the filtered regression.",
        action="store_true",
        default=False,
    )
    flags.add_argument(
        "--pdb",
        help="Invoke pdb at the end of the run, to inspect results.",
        action="store_true",
        default=False,
    )
    flags.add_argument(
        "--force-retrain",
        help="Force retraining.",
        action="store_true",
        default=False,
    )
    flags.add_argument(
        "--debug",
        help="Enable debug logging.",
        action="store_true",
        default=False,
    )
    flags.add_argument(
        "--keep-intermediates",
        help="Keep intermediate artifacts. Consumes additional disk space, but can be useful for debug.",
        action="store_true",
        default=False,
    )

    # figure out how to make this not required and give it a default
    cluster_opt = parser.add_mutually_exclusive_group(required=True)
    cluster_opt.add_argument(
        "--local-cluster",
        help="Run with a local dask cluster. Should only be used with bsub.",
        action="store_true",
        default=False,
    )
    cluster_opt.add_argument(
        "--no-cluster",
        help="Run without any cluster object. For debug.",
        action="store_true",
        default=False,
    )
    cluster_opt.add_argument(
        "--distributed",
        help="Run with a distributed dask cluster.",
        action="store_true",
        default=False,
    )
    opts = parser.parse_args()

    opts.fetch_train_from_date = datetime.strptime(opts.fetch_train_from_date , "%Y%m%d").date()
    opts.fetch_train_to_date = datetime.strptime(opts.fetch_train_to_date, "%Y%m%d").date()
    opts.fetch_train_usertag = ast.literal_eval(opts.fetch_train_usertag)

    return opts


def load_popeye_json_configs(json_files: List[str]) -> Dict:
    """
    Load json files from list of files.
    Return dictionary like so:
    output dictionary
    {
        <seed>: <config>,
        <seed>: <config>
        ...
    }
    :param json_files: List of strings containing file names
    :type json_files: list
    :return ret: Config dictionary from json
    :type ret: Dictionary
    :return fails: Fail info from json
    :type fails: Dictionary
    """

    ret = {}
    for path in json_files:
        with open(path, "r") as fd:
            json_dict = json.load(fd)

        if not json_dict:
            logger.info(f"{path} could not be loaded")
            continue

        ret[json_dict["stats"]["global"]["seed"]] = {
            "seed": json_dict["stats"]["global"]["seed"],
            "fail": 1 if "FAIL" in path else 0, "config": json_dict["config"],
            "build_options": json_dict["stats"]["global"]["build_options"],
            "command": json_dict["stats"]["global"]["command"]
        }

    return ret


@task()
def jsons_to_df(json_dir: str) -> pd.DataFrame:
    """
    Convert JSON file to dataframe.
    :param json_dir: Path location to pick json files from
    :return df: Output dataframe
    """

    files = glob.glob(str(json_dir) + "/popeye_elf*.json")

    config_dict = load_popeye_json_configs(files)

    flat_configs = {}
    for kconfig in config_dict:
        flat_configs[kconfig] = flatten_dict(config_dict[kconfig]["config"], sep="")
        flat_configs[kconfig]["fail"] = config_dict[kconfig]["fail"]
        flat_configs[kconfig]["seed"] = config_dict[kconfig]["seed"]
        flat_configs[kconfig]["build_options"] = config_dict[kconfig]["build_options"]
        flat_configs[kconfig]["command"] = config_dict[kconfig]["command"]

    df = pd.DataFrame(flat_configs).T
    df["seed"] = df.index
    df = df.reset_index(drop=True)

    df.to_csv("generated.csv")

    return df


@task()
def scatter(data: pd.DataFrame) -> None:
    """Task to scatter training data to the cluster.

    :param data: The data to scatter.
    """
    with worker_client() as client:
        client.scatter(data)


@task()
def concat(dfs: List[pd.DataFrame]) -> pd.DataFrame:
    """Task to merge several small dataframes into a single larger one.

    :param dfs: The dataframes to merge.
    :return: The merged dataframe.
    """
    return pd.concat(dfs)


def training_subsample(data: pd.DataFrame, num: int, csvfile: Optional[str]=None) -> pd.DataFrame:
    """Task to subsample the training data, preserving all failures.

    :param data: The training data.
    :param num: The number of samples to take.
    :param csvfile: If provided, the subsampled data will be written to a file
        with this name, defaults to None
    :return: The subsampled data.
    """
    # Keep all fails
    fail_index = data.loc[data.result == 'FAIL'].index

    # And then make up the difference with sampling.
    to_sample = num - len(fail_index)
    passing_index = data.sample(to_sample).index
    sampled = data.loc[fail_index.join(passing_index, how="outer")]

    if csvfile:
        sampled.to_csv(csvfile)

    if sampled.empty:
        logger.info("error data filtered by training_subsample() is empty!")
        raise ValueError

    return sampled


@task
def get_table_data(opts: argparse.Namespace, eap: EAPInterfaceS3) -> pd.DataFrame:
    """This task retrieves the tabular data for the training window.

    :param opts: Options given on the commandline which define the training window.
    :param eap: An instance of the ML4V EAP data loader.
    :return: The table data.
    """
    date_list = None
    delta = opts.fetch_train_to_date - opts.fetch_train_from_date
    date_list = [
        opts.fetch_train_from_date + timedelta(days=i) for i in range(delta.days + 1)
    ]

    dfs = []
    for date in date_list:
        data = eap.get_sets(
            date, date + timedelta(days=1) # , payload="popeye"
        )
        data = filter_data(opts, data)
        dfs.append(data)

    table_data = pd.concat(dfs)

    if opts.training_subsample:
        table_data = training_subsample(table_data, opts.training_subsample, 'subsampled.csv')

    if opts.date_as_sid:
        table_data = table_data.assign(date=table_data.uploadedAt.apply(lambda x: f'{x.year}-{x.month}-{x.day}'))

    if table_data.empty:
        logger.info("error data filtered by get_table_data() is empty!")
        raise ValueError

    return table_data


# This should NOT have the @task decorator; it generates tasks that go in the final flow graph.
def get_data(opts: argparse.Namespace, table_data: pd.DataFrame, eap: EAPInterfaceS3) -> Task:
    """This function generates the tasks which will be used to fetch the attachments
    and create the training data.

    :param opts: Options given on the commandline which define the training data.
    :param table_data: The table data for which the attachments should be fetched.
    :param eap: An instance of the ML4V EAP data loader.
    :return: A task which will generate the training dataset.
    """
    attachments = eap.attachments_from_rows(table_data, pattern=r"popeye\.json\.gz")
    configs = process_attachments(attachments)

    if opts.keep_intermediates:
        table_data_file = dt.files.dump_pickle(table_data, "get_data.table_data.pkl")
        configs_file = dt.files.dump_pickle(configs, "get_data.cfgs.pkl")

    training_data = build_training_data(table_data, configs)

    if opts.keep_intermediates:
        training_data_file = dt.files.dump_pickle(training_data, 'get_data.training_data.pkl')

    return training_data


@task
def build_training_data(dfret: pd.DataFrame, configs: Dict[str,str]) -> pd.DataFrame:
    """A task to build the training data from the raw data in EAP.

    :param dfret: The tabular data from EAP.
    :param configs: The JSON data attached in EAP.
    :raises ValueError: If the raw data is malformed.
    :return: The training data.
    """
    try:
        for key, value in configs.items():
            configs[key] = flatten_dict(value, sep="")
        config_df = pd.DataFrame(configs).T

        # seperate out an sid and rid column
        config_df["sid-rid-tuple"] = config_df.index.to_numpy()
        config_df = config_df.reset_index(drop=True)
        try:
            config_df["sid"] = config_df.apply(lambda r: r["sid-rid-tuple"][0], axis=1)
            config_df["rid"] = config_df.apply(lambda r: r["sid-rid-tuple"][1], axis=1)
            config_df = config_df.drop(columns=["sid-rid-tuple"])
        except ValueError as ve:
            logger.info("error building dataframe. possibly no data found")
            logger.info("config_df.shape = {}".format(config_df.shape))
            raise ve

        # if it didnt crash then it either passed or failed
        dfret = dfret[dfret.result != "CRASH"]
        dfret = dfret.drop(
            columns=dfret.columns.difference(
                [
                    "dut_config_label",
                    "result",
                    "test_seed",
                    "sid",
                    "rid",
                    "uploadedAt",
                    "fail_signature",
                ]
            )
        )

        dfret = dfret.rename(
            columns={"result": "fail", "test_seed": "SEED", "uploadedAt": "date"}
        )
        dfret["fail"] = dfret["fail"].map({"OK": 0, "FAIL": 1})

        # merge result data with config data
        dfret = pd.merge(
            dfret,
            config_df,
            how="inner",
            left_on=["sid", "rid"],
            right_on=["sid", "rid"],
        )
    except:
        logger.info("Exception Caught. Generating debug package.")
        if 'popeye_configs' in locals():
            logger.info("Writing ./configs.pkl")
            joblib.dump(configs, "./configs.pkl")
        logger.info("Writing ./dfret.pkl")
        joblib.dump(dfret, "./dfret.pkl")
        raise

    logger.info("Training data successfully created.")

    # The old workflow wrote data to CSV before ingesting it in this workflow. This had
    # the side effect of converting list objects to strings, which must be processed
    # differently. The application needs updating to handle list objects directly.
    dfret.to_csv("training_data.csv")
    dfret = pd.read_csv("training_data.csv", index_col=0)

    return dfret


@task
def process_attachments(attachments: Dict[str, ByteString]) -> Dict[str, str]:
    """A task to convert the attachment bytestreams into JSON strings.

    :param attachments: A dictionary containing all the JSON bytestreams.
    :return: A dictionary containing the JSON strings.
    """
    for key, value in attachments.items():
        decoded = zlib.decompress(value['popeye.json.gz'], 16 + zlib.MAX_WBITS).decode()
        attachments[key] = json.loads(decoded)["config"]
    return attachments


def filter_data(opts: argparse.Namespace, data: pd.DataFrame) -> pd.DataFrame:
    """Filter tabular data by user regression tag.

    :param opts: Namespace containing the regression tag(s) to search for.
    :param data: Tabular data from EAP.
    :return: The fitlered data.
    """
    if opts.keep_intermediates:
        joblib.dump(data, 'filter_data.data.pkl')
        joblib.dump(opts, 'filter_data.opts.pkl')

    def intersection(lista, listb):
        if set(lista) & set(listb):
            return True
        return False

    data = data.loc[data.apply(lambda x, y=opts.fetch_train_usertag:
                                    intersection(x.user_regression_tag, y), axis=1)]

    if data.empty:
        logger.info("error data filtered by filter_data() is empty!")
        # raise ValueError - decided to not raise an exception here, just rely on error message above

    return data


def main():
    opts = parse_args()

    popeye_project = get_project_from_env_variable()

    model_dir = pathlib.Path(f"/projects/pd/{popeye_project.project_directory}/machine_learning/model_store")

    json_dir = pathlib.Path(os.environ["POPEYE_HOME"]) / "ml_dump"
    output_dir = pathlib.Path(opts.output)

    testbench = "popeye"
    application = "bug_discovery"

    if opts.model_prefix:
        model_dir = model_dir / opts.model_prefix
    model_dir = model_dir / popeye_project.name / testbench / application
    logger.info( "Creating model in directory {}".format( model_dir))
    model_store = LocalModelStore(model_dir)

    # if we remove the allowed code we will retry if there's some blkval specific failure
    interface = PopeyeDoryInterface(allowed_codes=[1], clean_before_regress=True)
    dory_project = dory.Project(interface=interface, use_project_env=True)

    # EAP interface
    eap = EAPInterfaceS3(
        project='yeti',
        schema="ce_dynamic_test_schema",
        schema_version=4,
        io_workers=10,
        aws_profile="IPG-CE-EAP-PROD",
        bucket="aws-eu-west-1-eap-data-prod",
        production=False
        )

    preprocess_flow = PopeyePreprocessing(project_name=popeye_project.name)

    bug_discovery = BugDiscoveryFlow(force_retrain=opts.force_retrain, project_name=popeye_project.name)

    run_generate = opts.num_generate is not None
    run_filter = run_generate or opts.candidate_csv is not None
    run_regress = run_filter and not opts.no_run

    # Build the flow
    with Flow("flow") as flow:
        # Set up the filtering/inference data.
        x_pred = None
        if opts.candidate_csv:
            x_pred = dt.files.read_csv(opts.candidate_csv, index_col=0)
        if opts.num_generate:
            x_pred = jsons_to_df(json_dir)
            generate_results = dt.project.generate(dory_project, num_tests=opts.num_generate, json_dir=json_dir)
            x_pred.set_upstream(generate_results)

        # Get data from both sources and concatenate
        if opts.training_csv or opts.fetch_train_data:
            dfs = []
            if opts.fetch_train_data:
                table_data = get_table_data(opts, eap)
                df_eap = get_data(opts, table_data, eap)
                dfs.append(df_eap)

            if opts.training_csv:
                df_csv = dt.files.read_csv(opts.training_csv, index_col=0)
                dfs.append(df_csv)

            df_train = concat(dfs)

            # Prepare training data
            preprocess_result = preprocess_flow(df_train)

            x_train = preprocess_result[0]
            y_train = preprocess_result[1]
            groups = preprocess_result[2]

            # Scatter the training data to the cluster
            scatter_result = scatter([x_train, y_train, groups])
        else:
            x_train = None
            y_train = None
            groups = None

        if opts.keep_intermediates:
            x_pred_file = dt.files.dump_pickle(x_pred, "x_pred.pkl")

        # Call the application with the appropriate data
        bug_discovery_result = bug_discovery(
                x_train=x_train,
                y_train=y_train,
                groups=groups,
                x_pred=x_pred,
                n_run=opts.num_tests,
                run=run_regress,
                project=dory_project,
        )

    if opts.local_cluster:
        client = Client(processes=False, n_workers=1)
        executor = make_executor(client)
    if opts.distributed:
        client = start_cluster(
            min_workers=opts.min_workers,
            max_workers=opts.max_workers,
            debug=opts.debug,
            mem=opts.dask_memory * 1024 * 1024 * 1024,
            walltime=10000,
            job_extra=[f'-R "select[rhe7 && os64] rusage[mem={opts.dask_memory}G'
                         f',tmp=10]" -Jd dory -g /dask/dask_worker'],
            clean_logs=True
        )
        executor = make_executor(client)
    if opts.no_cluster:
        executor = None

    runner = FlowRunner(flow)

    with prefect.context(model_store=model_store):
        if not opts.pdb:
            with raise_on_exception():
                result = runner.run(
                    executor=executor, return_tasks=[bug_discovery_result]
                )
        else:
            result = runner.run(executor=executor, return_tasks=[bug_discovery_result])

    if opts.pdb:
        breakpoint()


if __name__ == "__main__":
    main()
