"""
"""
from .general_utils import LEXResult


NOT_INTERESTING = " \n\t"
CONTROL_CHARS = ";|&<>"


# Get result and output from LEX's response
def parse_result_and_output(response_json, func_name):
    if "result" not in response_json:
        raise Exception("[!] {}: Lambda response body doesn't contain 'result'".format(func_name))

    if "output" not in response_json:
        raise Exception("[!] {}: Lambda response body doesn't contain 'output'".format(func_name))

    return LEXResult(response_json["result"]) , response_json["output"]


# Checks if command has any meaningful chars
def is_interesting_cmd(cmd):
    for char in cmd:
        if char not in NOT_INTERESTING: # at least one interesting char
            return True
    return False


# Checks if command contains shell CONTROL_CHARS
def contains_shell_control_chars(cmd):
    for control_char in CONTROL_CHARS:
        if control_char in cmd:
            return True
    return False


# Check if abs_path
def is_abs_path(path):
    if path[0] == "/":
        return True
    return False


# trims redundant '/' from path 
def trim_redundant_slashes(path):
    while (len(path) > 1) and (path[-1] == "/"):
        path = path[:-1]
    return path


# Printable

INFO_PREFIX = "# splash: "
INVALID_CONFIG_CMD = "# Invalid config command: '{}'"
CONFIG_PARAM_MISSING = "# Missing parameter for 'splash config {}'"


IN_SHELL_COMMANDS = """# Special Commands:
\t-> Enter 'q' to exit. 
\t-> Enter '!gt(b) <lambda-path> <local-path>' to get a file to your local machine, '--gtb' is for binary mode.
\t-> Enter '!pt(b) <local-path> <lambda-path>' to put a file on the Lambda, '--ptb' is for binary mode.
\t-> Enter '!help' to display this message while in a shell session"""

USAGE = """# Usage:
  -> splash
  -> splash config  # get config 
  -> splash config addr <lambda-addr>
  -> splash config trackfs <true/false>
  -> splash config color <true/false>"""


HELP_STR = """
   _____        ____        __        ___         _____      __  __   
  / ___/       / __ \      / /       /   |       / ___/     / / / /   
  \__ \       / /_/ /     / /       / /| |       \__ \     / /_/ /      
 ___/ /      / ____/     / /___    / ___ |      ___/ /    / __  /      
/____/plash /_/seudo    /_____/   /_/  |_|mbda /____/    /_/ /_/ell  

A pseudo shell re-invoking the Lambda for each command.
\t -> SPLASH runs on your local machine.
\t -> LEX (Lambda Executor) should run on your Lambda.

To support certain features splash will run simple commands on the Lambda behind the scenes
(e.g. 'whoami' to get the user name)

-------------------------------------------------------------------

# Configuration:
\t-> splash config                      - get configuration
\t-> splash config addr <lambda-addr>   - set target Lambda
\t-> splash config trackfs <true/false> - track resets of the filesystem (the writable dir at '/tmp'), slows splash significantly.  
\t-> splash config color <true/false>   - enable/disable coloring

""" + IN_SHELL_COMMANDS + """

# Known Limitations:
\t-> Currently only works with open API Gateway endpoints.
\t-> Does not support environment variables.
\t-> File transfers are limited to the Lambda's max request/response size (6MB). splash will try to tar larger files.
\tIf the compressed file is still too large, consider running 'curl -F data=@path/to/lambda/file <your-server-address:port>' in splash.
\t-> Limited support for CWD tracking. 
\t\t* Supported by tracking 'cd' commands to identify the CWD, and then inserting "cd CWD; " to the start of shell commands.
\t\t* Piping commands with 'cd' isn't supported (i.e. "cd /tmp ; echo A")
\t\t* cd into an absolute path with '..' or '.' isn't supported (i.e. "cd /tmp/../tmp")
\t\t* splash can get 'stuck' in a deleted directory, run 'cd' to reset CWD
"""



