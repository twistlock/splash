import subprocess
import json
import os 
import base64
from traceback import format_tb

from lib.general_utils import * 

READ_BINARY = "rb"
WRITE = "w"

# if true, LEX will return traceback info when encountering unexpected exceptions
INCLUDE_TRACEBACK_IN_RESPONSE = False
if "LEX_TRACE" in os.environ:
    if os.environ["LEX_TRACE"] == "True":
        INCLUDE_TRACEBACK_IN_RESPONSE = True


"""
* Handler
"""
def handler(event, context):
    print("[+] LEX: Starting...")

    try:
        action, data = parse_action(event)

        # Bash commands
        if action == CMD_ACTION:
            return_code, out = run_cmd(data)
            return construct_cmd_response(return_code, out)
        
        # Get file 
        elif action == GETFILE_ACTION:
            if "file" not in data or "mode" not in data:
                return construct_response(LEXResult.ERR, "[!] Get file request should contain file and mode")
            result, out = run_getfile(data["file"], data["mode"])
            return construct_getfile_response(result, out)

        # Put file
        elif action == PUTFILE_ACTION:
            if "path" not in data or "content" not in data or "mode" not in data: 
                return construct_response(LEXResult.ERR, "[!] Put file request should contain path, content and mode")
            result, out = run_putfile(data["path"], data["content"], data["mode"])
            return construct_putfile_response(result, out)


    except Exception as e:
        return construct_exception_response(e)
        


def parse_action(event):
    """
    * Returns action, data from event
    """
    simple_response = False
    if "body" in event:
        body = json.loads(event["body"])
    else:
        body = event

    if ACTION in body:
        if body[ACTION] == CMD_ACTION:
            if CMD_ACTION in body:
                return CMD_ACTION, body[CMD_ACTION]
            else:
                raise Exception("[!] parse_action: cmd request does not include a command")
        
        elif body[ACTION] == GETFILE_ACTION:
            if GETFILE_ACTION in body:
                return GETFILE_ACTION, body[GETFILE_ACTION]
            else:
                raise Exception("[!] parse_action: getfile request does not include data")
        elif body[ACTION] == PUTFILE_ACTION:
            if PUTFILE_ACTION in body:
                return PUTFILE_ACTION, body[PUTFILE_ACTION]
            else:
                raise Exception("[!] parse_action: putfile request does not include data")
        else:
            raise Exception("[!] parse_action: Unknown action: {}".format(body["action"]))

    else:
        raise Exception("[!] parse_action: Request does not include an action")




def run_cmd(cmd):
    """
    * Runs a command as an external process
    """
    os.environ['PYTHONUNBUFFERED'] = "1"  # Required for streaming both stdout and stderr to stdout
    child = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out, _ = child.communicate()
    rc = child.returncode
    return rc, out


# returns LEXResult, output
def run_getfile(file, mode):
    # Check that file exists
    if not os.path.exists(file):
        return LEXResult.ERR, "run_getfile: file '{}' doesn't exist on Lambda".format(file)

    try:
        content = readfile(file, mode)

        # Base64 encode
        if type(content) is str:
            content = bytes(content.encode("utf8"))  # b64encode only excepts bytes.
        encoded = base64.b64encode(content)

        if len(encoded) < MAX_BODY_SIZE:
            return LEXResult.OK, encoded 

        # file too big, let's try to compress it
        content_len = len(content)
        encoded_len = len(encoded)
        del content, encoded    # delete large vars

        # Create tar file
        tar_path =  "/tmp/" + os.path.basename(file) + ".tar"
        create_tar_file(file, tar_path)

        # Read tar file and then delete it
        tar_content = readfile(tar_path, READ_BINARY)
        os.unlink(tar_path)

        # Send tar content if not too big
        tar_encoded = base64.b64encode(tar_content)
        if len(tar_encoded) < MAX_BODY_SIZE:
            return LEXResult.OK_TAR, tar_encoded

    except UnicodeDecodeError:
        return LEXResult.ERR, "run_getfile: reading file failed with UnicodeDecodeError, consider reading in binary mode (!gtb)"
    except IOError as e:
        return LEXResult.ERR, repr(e)

    # File too big....
    err_str =  "[!] File to big! size {}, encoded size {}, tar size {}, encoded tar size {}".format(\
        content_len, encoded_len, len(tar_content), len(tar_encoded))
    return LEXResult.ERR, err_str

# returns LEXResult, output
def run_putfile(path, content, writemode):

    decoded = base64.b64decode(str(content))

    # If not binary write, convert decoded into a string
    if writemode == WRITE: 
        decoded = decoded.decode("utf8") 

    try:
        # Write the received file
        writefile(path, writemode, decoded)
    except IOError as e:
        return LEXResult.ERR, "Failed to write to {} with: {}".format(path, repr(e))

    return LEXResult.OK, None



def construct_cmd_response(return_code, output):
    if return_code == 0:
        result = LEXResult.OK
    else:
        result = LEXResult.ERR
    
    return construct_response(result, output.decode("utf8"))  


def construct_getfile_response(result, output):
    if result != LEXResult.ERR: 
        output = output.decode("ascii") # if an err didn't occur, the output is base64 bytes. Let's convert into base64 string.
        
    return construct_response(result, output) 


def construct_putfile_response(result, output):
    return construct_response(result, output) 


def construct_exception_response(exception):
    if INCLUDE_TRACEBACK_IN_RESPONSE:
        # Prefix exception with traceback info
        display_exception = "LEX Traceback:\n" 
        for trace in format_tb(exception.__traceback__):
            display_exception += trace

    else:
        display_exception = "(set Lambda's env var 'LEX_TRACE' as 'True' for traceback info)\n"

    display_exception += str(repr(exception))

    return construct_response(LEXResult.LEX_EXCEPTION, display_exception) 


def construct_response(result, output):
    response = {
        "isBase64Encoded": False,
        "statusCode" : 200,
        "headers" : {"Content-Type" : "text/plain"},
        "body" : json.dumps({"result": result.value, "output": output})
    }
    return response 

