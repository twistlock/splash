#!/usr/bin/env python3
from sys import argv

from .config import get_lambda_addr
from .splash_utils import parse_result_and_output
from .general_utils import ACTION, CMD_ACTION

import requests
import json



DEFAULT_LAMBDA_ADDR = ""  # set if needed


def main():

    # Get Lambda address
    lambda_addr = get_lambda_addr()
    if not lambda_addr:
        if not DEFAULT_LAMBDA_ADDR:
            print("[!] Lambda address isn't set. Run 'splash config <lambda-addr>' or overwrite DEFAULT_LAMBDA_ADDR in this file ({}).".format(argv[0]))
            return
        lambda_addr = DEFAULT_LAMBDA_ADDR

    
    if len(argv) < 2:
        print("[+] Sends command to AWS lambda at {}\n[+] Usage: {} <args>".format(lambda_addr, argv[0]))
        return
        
    # Send command to lambda
    _, output  = send_command(argv[1:], lambda_addr)
    if not output:
        print("[+] Error getting response from lambda at {}".format(lambda_addr))
        return

    print(output)



def send_command(args, lambda_addr):

    """
    *
    * @Purpose:  Sends a command to the LEX (Lambda Executor) to execute.
    * @Params: args        -> list of form [cmd, arg1, arg2, ... argN]
    *          lambda_addr -> address of lambda
    *
    * @Returns: result -> LEXResult Enum
    *           output -> result data (For LEXResult.OK this is the command's output)
    *
    """
    post_data = {ACTION: CMD_ACTION, CMD_ACTION: args}

    response = requests.post(lambda_addr, json=post_data)
    if not response:
        raise Exception("[+] Didn't get response from lambda at {}".format(lambda_addr))
    
    decoded_response = response.content.decode('utf8') # bytes to string
    try:
        resp_json = json.loads(decoded_response)
    except json.decoder.JSONDecodeError as e:
        raise Exception("[!] send_command: Lambda response body isn't JSON decodeable") from e

    result, output = parse_result_and_output(resp_json, "send_command")
    return result, output
    



if __name__ == "__main__":
    main()
