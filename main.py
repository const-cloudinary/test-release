"""
This module generates packages from the OpenAPI spec.

It is meant to run in the Jenkins job, although it can be run independently.

See main function docstring for the required environment variables.
"""
import json
import logging
import os
import shutil
import subprocess
import sys

import yaml

OPEN_API_GEN = '/opt/homebrew/bin/openapi-generator'

logging.basicConfig(level=logging.INFO)


def camel_to_snake(s):
    return ''.join(['_' + c.lower() if c.isupper() else c for c in s]).lstrip("_").replace(" ", "")


def exit_with_error(msg):
    logging.error(msg)
    sys.exit(1)


def run_command(*args):
    """
    Executes the command with the arguments and exits in case of an error.
    :param args: The command name and the arguments.
    :return: result
    """
    result = subprocess.run(args)
    if result.returncode != 0:
        exit_with_error(result)

    return result


def main():
    """
    Generates the specified packages based on the environment variables.
    :return: 0 on success and any other status code on error
    """
    dry_run = os.getenv("DRY_RUN")

    api_spec = os.getenv("YML")
    """The source OpenApi spec YML file."""

    definition_file = os.getenv("DEFINITION_FILE")
    """The definition file of the code generation project, contains supported languages with other details."""
    sdks = os.getenv("SDKS")
    """Comma separated list of SDKs to generate."""

    org_name = os.getenv("ORG_NAME")
    """GitHub repository organization(usually cloudinary). Can be changed for testing."""

    sdks = sdks.split(",")

    if not sdks:
        logging.warning("No SDKs to generate...")
        return 0

    with open(definition_file, 'r') as f:
        spec = json.load(f)

    with open(api_spec, "r") as f:
        yml = yaml.safe_load(f)

    package = camel_to_snake(yml["info"]["title"])
    version = yml["info"]["version"]

    definitions = dict([(d.pop('value'), d) for d in spec["SDKS"]])

    if not all(key in definitions for key in sdks):
        exit_with_error(f"Missing definitions for {list(set(sdks) - set(definitions.keys()))} SDKs, aborting.")

    for sdk in sdks:
        repo_name = definitions[sdk]["repo"].format(package=package)
        template = definitions[sdk]["template"]

        shutil.rmtree(repo_name, ignore_errors=True)

        repo_url = f"git@github.com:{org_name}/{repo_name}.git"

        run_command("git", "clone", repo_url)

        run_command(OPEN_API_GEN, "generate", "-i", api_spec, "-g", template, "-o", repo_name)

        os.chdir(repo_name)

        run_command("git", "add", ".")

        run_command("git", "commit", "-m", f"Version {version}")
        run_command("git", "tag", "-a", version, "-m", f"Version {version}")

        if dry_run:
            logging.info("Dry Run, no further steps performed.")
            return 0

        # run_command("git", "push")
        # run_command("git", "push", "--tags")

        os.chdir("..")

    return 0


if __name__ == '__main__':
    # os.environ["YML"] = "https://raw.githubusercontent.com/CloudinaryLtd/service_interfaces/master/media-delivery/schema.yml?token=GHSAT0AAAAAABHTNHGTH4UHJTIJ2SOP4T2UYTPAIYA"
    # os.environ["DEFINITION_FILE"] = "https://raw.githubusercontent.com/const-cloudinary/test-release/master/sdk.json"
    # # os.environ["SDKS"] = "python,php,java,nodejs"
    # os.environ["SDKS"] = "php,nodejs"
    # os.environ["ORG_NAME"] = "const-cloudinary"

    main()
