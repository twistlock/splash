from .general_utils import readfile, writefile
import json
from pathlib import Path


# config file path
CONFIG_FILENAME = ".splash_config"
HOME = str(Path.home())
CONFIG_FILE_PATH = HOME + "/" + ".splash_config"


# config commands
LAMBDA_ADDR_KEY = "addr"
FS_TRACKING_KEY= "trackfs"
COLOR_KEY = "color"



## Config funcs ##

def get_config():
    try:
        config_data = readfile(CONFIG_FILE_PATH, "r")
    except FileNotFoundError:
        return {}
    try:
        return json.loads(config_data)
    except json.JSONDecodeError:
        return {}

def print_config():
    config = get_config()
    print(json.dumps(config, indent=4, sort_keys=True))

def get_lambda_addr():
    config = get_config()
    if LAMBDA_ADDR_KEY in config:
        return config[LAMBDA_ADDR_KEY]
    else:
        return None

def get_fs_tracking():
    config = get_config()
    if FS_TRACKING_KEY in config:
        return config[FS_TRACKING_KEY]
    else:
        return None

def get_color():
    config = get_config()
    if COLOR_KEY in config:
        return config[COLOR_KEY]
    else:
        return None

def set_lambda_addr(addr):
    addr = addr[0]
    config = get_config()
    config[LAMBDA_ADDR_KEY] = addr
    writefile(CONFIG_FILE_PATH, "w", json.dumps(config))


def set_fs_tracking(is_track):
    is_track = is_track[0]
    if is_track == "true":
        is_track = True
    elif is_track == "false":
        is_track = False
    else:
        print("[+] Usage: splash config fs_track <true/false>")
        return

    config = get_config()
    config[FS_TRACKING_KEY] = is_track
    writefile(CONFIG_FILE_PATH, "w", json.dumps(config))


def set_color(is_color):
    is_color = is_color[0]
    if is_color == "true":
        is_color = True
    elif is_color == "false":
        is_color = False
    else:
        print("[+] Usage: splash config color <true/false>")
        return

    config = get_config()
    config[COLOR_KEY] = is_color
    writefile(CONFIG_FILE_PATH, "w", json.dumps(config))


CONFIG_CMDS = {"addr": set_lambda_addr, "trackfs": set_fs_tracking, "color": set_color}
