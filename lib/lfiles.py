import requests
import json

from .splash_utils import parse_result_and_output
from .general_utils import ACTION, GETFILE_ACTION, PUTFILE_ACTION


def send_getfile_command(file, mode, lambda_addr):
    post_data = {ACTION: GETFILE_ACTION, GETFILE_ACTION: {"file" : file, "mode" : mode} }
    response = requests.post(lambda_addr, json=post_data)
    if not response:
        raise Exception("[+] Didn't get response from lambda at {}".format(lambda_addr))

    resp_json = json.loads(response.content.decode("utf8"))

    result, output = parse_result_and_output(resp_json, "send_getfile_command")
    return result, output


def send_putfile_command(path, content, writemode, lambda_addr):
    post_data = {"action": PUTFILE_ACTION, PUTFILE_ACTION: {"path": path, "content" : content, "mode" : writemode} }
    response = requests.post(lambda_addr, json=post_data)
    if not response:
        raise Exception("[+] Didn't get response from lambda at {}".format(lambda_addr))
    data = json.loads(response.content.decode("utf8"))

    resp_json = json.loads(response.content.decode("utf8"))

    result, output = parse_result_and_output(resp_json, "send_putfile_command")
    return result, output






