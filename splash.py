#!/usr/bin/env python3

from lib.lcmd import send_command
from lib.lfiles import send_getfile_command, send_putfile_command
from lib.colors import colored, colored_for_input
from lib.general_utils import LEXResult, MAX_BODY_SIZE, readfile, writefile, create_tar_file
from lib.splash_utils import *
from lib.config import *

import os
import readline  # changes python's input function to add shell like features (e.g. command history)
import base64
import requests
from sys import argv

# Commands
HELP = ["-h", "--h", "--help", "help"]
CONFIG = "config"

# Default config
DEFAULT_TRACK_FS = False  # an option to track if the filesystem changed after each command, slows splash significantly.
DEFAULT_USE_COLOR = True  # present shell with color by default
USE_COLOR = DEFAULT_USE_COLOR

# Lambda FS state tracking consts
INDICATOR_DEFAULT_PATH = "/tmp/.splash_fs_state_indicator.do_not_delete"
NEW_FS = True
SAME_FS = False
CONT_FSTRACK = True
STOP_FSTRACK = False

# Consts
EXIT_CMDS = ["q", "exit"]
EMPTY_CWD = ""
ROOT_DIR = "/"

# File IO
READ_BINARY = "rb"
WRITE_BINARY = "wb"
READ = "r"
WRITE = "w"


def main(lambda_addr, try_to_fs_track):
    # Print welcome
    print_info("Talking to {}".format(lambda_addr))
    print_info("For help, enter '!help'")

    # Get Lambda's user and default working dir
    try:
        usr, cwd = init_shell_params(lambda_addr)
    except (requests.exceptions.InvalidURL, requests.exceptions.MissingSchema) as urlException:
        print("# Invalid lambda url: {}".format(lambda_addr))
        return
    lambda_original_cwd = cwd

    if try_to_fs_track:
        print_info("FS tracking ON")

    # Check if Lambda fs state from last session was preserved
    is_new_fs_instance, continue_fs_tracking = check_is_new_fs_instance(INDICATOR_DEFAULT_PATH, lambda_addr)
    if continue_fs_tracking:  # Only print if there was no error
        if is_new_fs_instance:
            print_info("Lambda filesystem was reset / First time running splash with this Lambda\n")
        else:
            print_info("Lambda filesystem state from previous splash session is preserved\n")

    # continue tracking if the user config asked for it AND there was no error
    continue_fs_tracking = try_to_fs_track and continue_fs_tracking

    # Run shell
    shell_loop(lambda_addr, usr, cwd, lambda_original_cwd, continue_fs_tracking)


def shell_loop(lambda_addr, usr, cwd, lambda_original_cwd, continue_fs_tracking):
    is_new_fs_instance = False  # for first time in loop

    # Construct shell prefix as'USR@LAMBDANAME:CWD$ '
    lambda_name = extract_lambda_name(lambda_addr)
    if USE_COLOR:
        prefix = colored_for_input(usr + "@" + lambda_name, ["GREEN", "BOLD"]) + ":"
    else:
        prefix = usr + "@" + lambda_name + ":"

    while True:
        # Alert if we identified a filesystem reset
        if continue_fs_tracking and is_new_fs_instance:
            print_info("Function filesystem was reset")
            is_new_fs_instance = False

            # Append CWD to prefix
        if USE_COLOR:
            displayed_str = prefix + colored_for_input(cwd, ["BLUE", "BOLD"]) + "$ "
        else:
            displayed_str = prefix + cwd + "$ "

        # Get user input
        try:
            inpt = input(displayed_str)
        except KeyboardInterrupt:  # for ctrl+c
            print("")
            continue
        stripped_inpt = inpt.strip()

        if stripped_inpt in EXIT_CMDS:
            return  # exit...

        # Handle quick cases
        if not is_interesting_cmd(inpt):
            continue

            # Get file from lambda
        if stripped_inpt.startswith("!gt"):
            handle_getfile(stripped_inpt, lambda_addr, cwd)

        # Put file on lambda
        elif stripped_inpt.startswith("!pt"):
            handle_putfile(stripped_inpt, lambda_addr, cwd)

        # Reset CWD
        elif stripped_inpt == 'cd':
            cwd = lambda_original_cwd

        # Print help
        elif stripped_inpt == '!help':
            print(IN_SHELL_COMMANDS)
            continue

        # Ok so this is a regular shell command
        else:
            # make sure to cd to CWD before running the command 
            if cwd != EMPTY_CWD and cwd != lambda_original_cwd:  # no need if the CWD is the lambda_original_cwd
                cmd = "cd " + cwd + " && " + inpt
            else:
                cmd = inpt

            # Warp command with bash and send to lambda
            bash_cmd = ["bash", "-c", cmd]
            result, output = send_command(bash_cmd, lambda_addr)
            if result == LEXResult.LEX_EXCEPTION:
                print_info("LEX (Lambda Executor) encountered an unexpected exception while handling the bash command:\n"
                           + output)
                continue

            print(decode_output(output), end='')  # don't add newline

            # Try tracking the CWD
            cwd = track_cwd(cwd, inpt, (result != LEXResult.OK), lambda_addr)

        # Check if file system changed
        if continue_fs_tracking:
            is_new_fs_instance, continue_fs_tracking = check_is_new_fs_instance(INDICATOR_DEFAULT_PATH, lambda_addr)


# returns usr, cwd
def init_shell_params(lambda_addr):
    # Get user name
    result, output = get_whoami(lambda_addr)
    if result == LEXResult.OK:
        usr = output.rstrip()
    else:
        usr = ""
        print_info("Failed to get user name")

    # Get lambda default CWD
    result, output = get_pwd(lambda_addr)
    if result == LEXResult.OK:
        cwd = output.rstrip()
    else:
        cwd = ""
        print_info("Failed to get lambda initial cwd")

    return usr, cwd


# Checks indicator file to see if filesystem state is preserved.     
# Returns is_new_fs_instance, no_tracking_error
def check_is_new_fs_instance(indicator_path, lambda_addr):
    # Check is indicator file exists
    stat_cmd = ["stat", indicator_path]
    result, output = send_command(stat_cmd, lambda_addr)
    if result == LEXResult.OK:
        return SAME_FS, CONT_FSTRACK  # Indicator file exists
    if result == LEXResult.LEX_EXCEPTION:
        print_info("Failed to stat filesystem state file, from here on FS tracking is disabled. Exception:\n" + output)
        return SAME_FS, STOP_FSTRACK  # We return SAME_FS so nothing will be printed aside from the error message

    # Ok so new instance, lets create the indicator
    cmd = "touch " + indicator_path
    bash_cmd = ["bash", "-c", cmd]
    result, output = send_command(bash_cmd, lambda_addr)

    # Check if creating indicator file failed
    if result != LEXResult.OK:
        print_info("Failed to create a new indicator file, from here on FS tracking is disabled. Error : " + output)
        return NEW_FS, STOP_FSTRACK  # new fs, creating indicator failed

    return NEW_FS, CONT_FSTRACK  # new fs, creating indicator succeeded


def decode_output(output):
    # If output is still bytes, it means it isn't Unicode compatible
    # The best we can do is remove the b'' wrapping
    if type(output) is bytes:
        output = str(output)[2:-1]
    return output


def handle_getfile(inpt, lambda_addr, cwd):
    args = inpt.split(' ')
    if len(args) != 3:
        print_info("[!] Usage: '!gt(b) <lambda-abs-path> <local-abs-path>'")
        return

    local_path = args[2]
    lambda_path = args[1]
    if not is_abs_path(lambda_path):
        lambda_path = os.path.join(cwd, lambda_path)  # handle relative lambda paths

    if inpt.startswith("!gtb"):
        getfile(lambda_path, local_path, READ_BINARY, WRITE_BINARY, lambda_addr)
    else:
        getfile(lambda_path, local_path, READ, WRITE, lambda_addr)


def handle_putfile(inpt, lambda_addr, cwd):
    args = inpt.split(' ')
    if len(args) != 3:
        print_info("[!] Usage: '!pt(b) <local-path> <lambda-abs-path>'")
        return

    local_path = args[1]
    lambda_path = args[2]
    if not is_abs_path(lambda_path):
        lambda_path = os.path.join(cwd, lambda_path)  # handle relative lambda paths

    if inpt.startswith("!ptb"):
        putfile(lambda_path, local_path, READ_BINARY, WRITE_BINARY, lambda_addr)
    else:
        putfile(lambda_path, local_path, READ, WRITE, lambda_addr)


# Receives file from Lambda. Prints outcome. No return value
def getfile(lambda_path, local_path, read_mode, write_mode, lambda_addr):
    print_info("Getting file {}, for large files this might take a few seconds...".format(lambda_path))
    result, output = send_getfile_command(lambda_path, read_mode, lambda_addr)

    # LEXResult.ERR is for known errors (i.e. file doesn't exist)
    if result == LEXResult.ERR:
        print_info(output)
        # LEX encountered and unexpected exception
    elif result == LEXResult.LEX_EXCEPTION:
        print_info(
            "LEX (Lambda Executor) encountered an unexpected exception while handling the getfile command:\n" + output)

    else:
        # If we received a compressed version, change to binary write mode
        if result == LEXResult.OK_TAR:
            local_path += ".tar"
            write_mode = WRITE_BINARY

            # Decode the base64 output
        decoded_output = base64.b64decode(str(output))
        if write_mode == WRITE:
            decoded_output = decoded_output.decode("utf-8")  # convert to string if non-binary write

        try:
            writefile(local_path, write_mode, decoded_output)  # write received file
        except IOError:
            print_info("Couldn't open local file {} for writing".format(local_path))
            return

        # Print to user
        if result == LEXResult.OK:
            print_info("Copied {} from the Lambda to {} on the local machine".format(lambda_path, local_path))
        else:
            print_info("Compressed (bz2) and copied {} from the Lambda to {} on the local machine".format(lambda_path,
                                                                                                          local_path))


# Sends file to Lambda. Prints outcome. No return value
def putfile(lambda_path, local_path, read_mode, write_mode, lambda_addr):
    # Check that file exists
    if not os.path.exists(local_path):
        print_info("[!] putfile: file '{}' doesn't exist".format(local_path))
        return
    # Try to read the file
    try:
        content = readfile(local_path, read_mode)
    except UnicodeDecodeError:
        print_info("[!] putfile: reading file {} failed with UnicodeDecodeError, consider binary mode (use !ptb)".format(
                local_path))
        return
    except IOError as e:
        print_info("[!] putfile: reading file {} failed with IOError: ".format(local_path) + str(e))
        return

    # b64 encode
    if type(content) == str:
        content = bytes(content.encode("utf8"))  # b64encode only accepts bytes
    encoded = base64.b64encode(content).decode('utf8')
    is_tar = False

    encoded_len = len(encoded)
    content_len = len(content)
    del content

    # Check if file too big
    if len(encoded) >= MAX_BODY_SIZE:
        # file too big, let's try to tar it
        del encoded

        print_info("File is too big, trying to compress it, might take a minute...")

        # Create temp tar file
        tar_path = "/tmp/" + os.path.basename(local_path) + ".tar"
        create_tar_file(local_path, tar_path)

        # Read from temp tar and then delete it
        tar_content = readfile(tar_path, READ_BINARY)
        os.unlink(tar_path)

        # B64 Encode
        tar_encoded = (base64.b64encode(tar_content)).decode('ascii')
        if len(tar_encoded) >= MAX_BODY_SIZE:
            # still too big..
            print_info("[!] File still too big! size {}, b64 encoded size {}, tar size {}, b64 encoded tar size {}".format(
                    content_len, encoded_len, len(tar_content), len(tar_encoded)))
            return

        # Adjust params for tar file
        lambda_path += ".tar"
        encoded = tar_encoded
        write_mode = WRITE_BINARY  # tar is a bin
        is_tar = True

    # Send file
    result, output = send_putfile_command(lambda_path, encoded, write_mode, lambda_addr)

    if result == LEXResult.ERR:
        print_info(output)  # print Error info
        return
    elif result == LEXResult.LEX_EXCEPTION:
        print_info("LEX (Lambda Executor) encountered an unexpected exception while handling the putfile command:\n" + output)
        return

    # Prints success
    if not is_tar:
        print_info("Copied {} from the local machine to {} on the lambda".format(local_path, lambda_path))
    else:
        print_info("Compressed and copied {} from the local machine to {} on the lambda".format(local_path, lambda_path))


def track_cwd(previous_cwd, inpt, err, lambda_addr):
    """
    * A simple attempt to track CWD
    * Returns the new CWD if all goes well, or EMPTY_CWD if failed to track.
    """
    if ("cd " not in inpt) or err:
        # no need to track if not cd command or if command failed 
        return previous_cwd

    # OK, so we just run a successful cd command, let's try to find the new CWD

    # Can't track if the cd command contained shell control chars
    if contains_shell_control_chars(inpt):
        print_info("You entered a 'cd' command with shell control chars, this breaks cwd tracking. Do not trust the CWD displayed")
        return EMPTY_CWD

    cd_arg = inpt.split("cd")[1].strip()
    # easy case
    if is_abs_path(cd_arg):
        # if someone does something annoying like 'cd /tmp/../home' we won't sanitize it will be presented as the CWD
        return trim_redundant_slashes(cd_arg)

        # Ok this is a relative path
    else:
        # Handle common case of ..
        if cd_arg == "..":
            path_without_last_dir, _ = os.path.split(previous_cwd)
            return path_without_last_dir

        new_cwd = os.path.join(previous_cwd, cd_arg)
        if '.' not in cd_arg and '~' not in cd_arg:
            return trim_redundant_slashes(new_cwd)

        # cd command used either  '..', '.' or '~'. Let's let Bash on the lambda resolve that
        result, pwd_output = get_pwd(lambda_addr, cd_target=new_cwd)
        if result == LEXResult.OK:
            return pwd_output.rstrip()
        else:
            print_info("Failed to track CWD, do not trust the CWD displayed. Avoid using paths with '.', '~' and '..'")
            return EMPTY_CWD


# Get Lambda user
def get_whoami(lambda_addr):
    whoami_cmd = ["whoami"]
    result, output = send_command(whoami_cmd, lambda_addr)
    return result, output


# Runs pwd on the Lambda
def get_pwd(lambda_addr, cd_target=""):
    if cd_target:  # option to cd first, mainly to let bash resolve '..', '.', etc.
        cmd = "cd " + cd_target + " ; pwd"
    else:
        cmd = "pwd"
    bash_cmd = ["bash", "-c", cmd]
    result, output = send_command(bash_cmd, lambda_addr)
    return result, output


def print_info(msg):
    if USE_COLOR:
        print(colored(INFO_PREFIX, ["HEADER"]) + msg)
    else:
        print(INFO_PREFIX + msg)


def handle_not_shell_use_cases():
    """
    * Handle 'config' and 'help' commands
    """
    # Help
    if argv[1] in HELP:
        print(HELP_STR)

    # Config
    elif argv[1] == CONFIG:
        # if no config cmd specified, print config
        if len(argv) == 2:
            print_config()
            return

        config_cmd = argv[2]  # get config cmd

        if config_cmd not in CONFIG_CMDS:
            if config_cmd in HELP:
                print(USAGE)
            else:
                print(INVALID_CONFIG_CMD.format(config_cmd))
                print(USAGE)
            return

        if len(argv) == 3:
            print(CONFIG_PARAM_MISSING.format(config_cmd))
            print(USAGE)
            return

        param_list = argv[3:]  # pass as list to support config cmds with multiple args in the future
        config_func = CONFIG_CMDS[config_cmd]

        # Run appropriate config func
        config_func(param_list)

    else:
        print(USAGE)


if __name__ == "__main__":
    if len(argv) > 1:
        handle_not_shell_use_cases()
        exit(1)

    # Get config
    config = get_config()
    if LAMBDA_ADDR_KEY not in config:
        print("[!] Lambda address not configured. Run 'splash config addr <lambda-addr>")
        exit(1)
    lambda_addr = config[LAMBDA_ADDR_KEY]

    # get fs_tracking config
    fs_tracking = DEFAULT_TRACK_FS
    if FS_TRACKING_KEY in config:
        fs_tracking = config[FS_TRACKING_KEY]
    # get color config
    if COLOR_KEY in config:
        USE_COLOR = config[COLOR_KEY]

    main(lambda_addr, fs_tracking)
