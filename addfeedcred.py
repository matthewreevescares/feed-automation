import os
import argparse
import git
import sys
from loguru import logger
import ruamel
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
import subprocess
from readconfig import ReadConfig
#from getgenpass import GenpassMac
import distutils.util


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-t",
        "--ticket",
        type=str,
        help="Client Name (this gets normalized to lowercase)",
        required=True,
    )
    parser.add_argument(
        "-c",
        "--client",
        type=str,
        help="Client Name (this gets normalized to lowercase)",
        required=True,
    )
    parser.add_argument(
        "-u",
        "--person",
        type=str,
        help="The name of the user running this action",
        required=True,
    )
    parser.add_argument("--user", nargs="?")
    return parser.parse_args()


# setup
yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yaml.explicit_start = True


def get_genpass(length: int):
    result = subprocess.run(["genpass", str(length)], stdout=subprocess.PIPE)
    if result.returncode != 1:
        pass
    else:
        raise AssertionError("Calling genpass was not sucessfull")

    output = result.stdout.decode("utf-8").split(":")
    return output


def get_password_hash(length):
    input = get_genpass(length)
    output = {}
    output["password"] = input[1].split("\n").pop(0).strip()
    output["hash"] = input[-1].strip()
    return output


def get_configs():
    return [x for x in os.scandir(config_filelocation) if x.name == feed_filename]


def strip_endding_new_line(stream):
    return stream.rstrip()


def process_file(filename):
    with open(filename) as fdesc:
        try:
            body = ruamel.yaml.round_trip_load(fdesc, preserve_quotes=True)
        except:
            logger.warning("Failed to load {filename}", filename=filename)
            return False

    old_body = body
    if not old_body:
        return False

    try:
        old_body
    except KeyError:
        return False
    except TypeError:
        pass

    body["groups"]["prod-feedrecv"]["feed_partner_credentials"].update(
        {client.lower(): DoubleQuotedScalarString(hash)}
    )
    temp = body["groups"]["prod-feedrecv"]["feed_partner_credentials"]
    body["groups"]["prod-feedrecv"]["feed_partner_credentials"] = dict(
        sorted(temp.items(), key=lambda x: x[0].lower())
    )
    with open(filename, "w") as fdesc:
        yaml.dump(body, fdesc, transform=strip_endding_new_line)
        fdesc.write("\n")
        yaml.dump(body, sys.stdout)
    return body


def query_yes_no(question, default="no"):
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError(f"Unknown setting '{default}' for default.")

    while True:
        try:
            resp = input(question + prompt).strip().lower()
            if default is not None and resp == "":
                return default == "yes"
            else:
                return distutils.util.strtobool(resp)
        except ValueError:
            print("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def run_git(gitrepo):
    repo = git.Repo(gitrepo, search_parent_directories=True)

    diffs = repo.index.diff(None, create_patch=True)

    if not len(diffs) > 1:
        for diff in repo.index.diff(None, create_patch=True):
            print(diff)
            ans = query_yes_no("Do you want to save?")
            if not ans:
                repo.git.checkout("--", config_filename)
                sys.exit(0)
    else:
        print("Failed to find any diffs or an untracked file exist in the directory")
        sys.exit(0)

    if diffs:
        commit_message = "{} Added New Hash For {} -{}".format(
            args.ticket, args.client, args.person.upper()
        )
        print("Committing {}".format(commit_message))
        repo.index.add(config_filename)
        repo.index.commit(commit_message)
        return True
    else:
        print("Failed to find any diffs")


if __name__ == "__main__":
    args = get_args()
    client = args.client.lower()
    user = args.user
    config = ReadConfig().read_configfile()
    password_length = config["configs"]["password_length"]

    if config["configs"]["env"]:
        password_and_hash = get_password_hash(password_length)
        feed_filename = config["configs"]["dev"]["file_name"]
        config_filename = config["configs"]["dev"]["git_file_name"]
        config_filelocation = config["configs"]["dev"]["working_dir"]
        gitrepo = config["configs"]["dev"]["git_repo"]
        hash = password_and_hash["hash"]
        password = password_and_hash["password"]
    else:
        password_and_hash = get_password_hash(password_length)
        feed_filename = config["configs"]["prod"]["file_name"]
        config_filename = config["configs"]["prod"]["git_file_name"]
        config_filelocation = config["configs"]["prod"]["working_dir"]
        gitrepo = config["configs"]["prod"]["git_repo"]
        hash = password_and_hash["hash"]
        password = password_and_hash["password"]

    configs = get_configs()
    for config in configs:
        # TODO Remove logger before prod
        # logger.info("Processing {filename}", filename=config)
        changes = process_file(config)
        # logger.info(
        #     "Completed {filename} changes={changes}", filename=config, changes=changes
        # )
    if run_git(gitrepo):
        keeper_website = "https://keepersecurity.com/vault/#"
        print(
            f" User: {client.title()}\n Password: {password}\n Site: {keeper_website}"
        )
