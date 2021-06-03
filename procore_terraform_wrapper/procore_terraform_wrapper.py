#!/usr/bin/env python3
from typing import List
import logging
import subprocess
import argparse
import os
import re
import sys

# setup logging
logging.basicConfig(level='INFO', format='%(asctime)s:%(levelname)s:%(message)s')
logger = logging.getLogger(__name__)


def run_os_command(args: List[str], input: str = "") -> subprocess.CompletedProcess:
    """
    Runs and logs OS commands.
    :param args: The list of command arguments to pass to subprocess
    :param input: An optional string to supply as input to the command.
    :return: CompletedProcess instance
    """
    logger.info('Running command: %s', " ".join(args))
    completed_process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, input=input)
    logger.info(f'Command completed. returncode={completed_process.returncode}')
    logger.debug(completed_process)
    return completed_process


def reduce_init(input: str) -> str:
    """
    Removes unnecessary parts of the output of `terraform init`. This removes the messages related to downloading modules.
    :param input: The output from `terraform init`
    :return: The shortened `terraform init` output.
    """
    match = re.search(r"(.*?Initializing modules\.\.\.\n).+?(Initializing the backend\.\.\..+$)", input, re.DOTALL)
    if(match):
        input = match.expand(r"\1 Module downloads removed for brevity\n\2")
    else:
        logger.warning('Failed to match regex for terraform init replacement. Please report this to the Atlantis maintainers as a bug!')
    return input


def reduce_plan(input: str) -> str:
    """
    Removes unnecessary parts of the output of `terraform plan`. This removes the messages related to the state refresh.
    :param input: The output from `terraform plan`
    :return: The shortened `terraform plan` output.
    """
    match = re.search(r"(.+?persisted to local or remote state storage\.\n).+?(---------.+$)", input, re.DOTALL)
    if(match):
        input = match.expand(r"\1 State refresh removed for brevity\n\2")
    else:
        logger.warning('Failed to match regex for terraform init replacement. Please report this to the Atlantis maintainers as a bug!')
    return input


def terraform_init(atlantis_terraform_executable: str, comment_args_list: List[str]) -> subprocess.CompletedProcess:
    """
    Runs `terraform init`. Will shorten the output if the command succeeds.
    :param atlantis_terraform_executable: The name of the terraform executable to use. (e.g. terraform0.13.6 or terraform)
    :param comment_args_list: List of extra args to supply to terraform command
    :return: The CompletedProcess instance from running terraform.
    """
    # terraform$ATLANTIS_TERRAFORM_VERSION init -input=false -no-color
    logger.info('Running terraform init...')
    tf_completed_process = run_os_command([atlantis_terraform_executable, 'init', '-input=false', '-no-color', *comment_args_list])
    # if terraform succeeded, run the reduce function to strip unnecessary output.
    if(tf_completed_process.returncode == 0):
        tf_completed_process.stdout = reduce_init(tf_completed_process.stdout)
    return tf_completed_process


def terraform_plan(atlantis_terraform_executable: str, comment_args_list: List[str], planfile: str) -> subprocess.CompletedProcess:
    """
    Runs `terraform plan`. Will shorten the output if the command succeeds.
    :param atlantis_terraform_executable: The name of the terraform executable to use. (e.g. terraform0.13.6 or terraform)
    :param comment_args_list: List of extra args to supply to terraform command
    :return: The CompletedProcess instance from running terraform.
    """
    # terraform$ATLANTIS_TERRAFORM_VERSION plan -input=false -refresh -no-color -out $PLANFILE | tfmask
    logger.info('Running terraform plan...')
    tf_completed_process = run_os_command([atlantis_terraform_executable, 'plan', '-input=false', '-refresh', '-no-color', '-out', planfile, *comment_args_list])
    # if terraform succeeded, run the reduce function to strip unnecessary output.
    if(tf_completed_process.returncode == 0):
        tf_completed_process.stdout = reduce_plan(tf_completed_process.stdout)
    return tf_completed_process


def terraform_apply(atlantis_terraform_executable: str, comment_args_list: List[str], planfile: str) -> subprocess.CompletedProcess:
    """
    Runs `terraform apply`.
    :param atlantis_terraform_executable: The name of the terraform executable to use. (e.g. terraform0.13.6 or terraform)
    :param comment_args_list: List of extra args to supply to terraform command
    :return: The CompletedProcess instance from running terraform.
    """
    # terraform$ATLANTIS_TERRAFORM_VERSION apply -no-color $PLANFILE | tfmask
    logger.info('Running terraform apply...')
    return run_os_command([atlantis_terraform_executable, 'apply', '-no-color', *comment_args_list, planfile])


def main_cli() -> int:
    """
    Main CLI method
    """
    # parse arguments
    parser = argparse.ArgumentParser(description='Wraps calls to terraform and tfmask. For use with Atlantis.')
    parser.add_argument('--action', choices=['init', 'plan', 'apply'], type=str, required=True, help='The Terraform command to perform.')
    args = parser.parse_args()

    # grab Atlantis environment variables
    atlantis_terraform_version = os.environ.get('ATLANTIS_TERRAFORM_VERSION', '')
    atlantis_terraform_executable = f'terraform{atlantis_terraform_version}'
    planfile = os.environ.get('PLANFILE', 'plan.tfplan')
    comment_args = os.environ.get('COMMENT_ARGS', '')
    comment_args_list = comment_args.split(',')

    # run the right function based on args
    if(args.action == 'init'):
        tf_completed_process = terraform_init(atlantis_terraform_executable, comment_args_list)
    elif(args.action == 'plan'):
        tf_completed_process = terraform_plan(atlantis_terraform_executable, comment_args_list, planfile)
    elif(args.action == 'apply'):
        tf_completed_process = terraform_apply(atlantis_terraform_executable, comment_args_list, planfile)

    # run tfmask, piping the terraform_output to it
    tfmask_completed_process = run_os_command(['tfmask'], input=tf_completed_process.stdout)

    # print masked output from tfmask
    print(tfmask_completed_process.stdout)

    # return exit code based on return code of original terraform command
    return tf_completed_process.returncode


if __name__ == '__main__':
    sys.exit(main_cli())
