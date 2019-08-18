"""
*
* Utils required by both splash and LEX
*
"""

import tarfile
import os
from enum import Enum

MAX_PAYLOAD_SIZE = 6291456  # 6MB
MAX_BODY_SIZE = MAX_PAYLOAD_SIZE - 500 # give some room for our headers


class LEXResult(Enum):
    """
    * Enum of possible results from LEX (Lambda Executor)
    
    """
    OK = 1             # action successful

    ERR = 2            # for regular shell commands, indicates non-zero exit code. 
                       # for file actions, indicates an expected error occurred (i.e. file doesn't exist on Lambda for a getfile operation)

    OK_TAR = 3         # for file actions, indicates file transfer was successful and the file was compressed

    LEX_EXCEPTION = 4  # LEX raised an unexpected exception


# Actions # 

ACTION = "action"
CMD_ACTION = "cmd"
GETFILE_ACTION = "getfile"
PUTFILE_ACTION = "putfile"


# File operations #

def readfile(path, mode):
    with open(path, mode) as f:
        return f.read()

def writefile(path, mode, data):
    with open(path, mode) as f:
        return f.write(data)

def create_tar_file(inputfile, output_path):
    """
    * Create a tar file at output_path and append the inputfile into it
    """
    with tarfile.open(output_path, "w:bz2") as tar:
        tar.add(inputfile, arcname=os.path.basename(inputfile))
