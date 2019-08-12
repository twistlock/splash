#!/usr/bin/env python3
from lib.lcmd import send_command
from lib.splash_utils import get_lambda_addr

from sys import argv
import requests



DEFAULT_LAMBDA_ADDR = ""   # set if needed

def main():
    """
    * Runs commands via bash on a remote AWS Lambda
    """

    # Get Lambda address
    lambda_addr = get_lambda_addr()
    if not lambda_addr:
        if not DEFAULT_LAMBDA_ADDR:
            print("[!] Lambda address isn't set. Run 'splash config <lambda-addr>' or overwrite DEFAULT_LAMBDA_ADDR in this file ({}).".format(argv[0]))
            return
        lambda_addr = DEFAULT_LAMBDA_ADDR

    # Check args
    if len(argv) < 2:
        print("[+] Sends command to AWS lambda at {}\n[+] Usage: {} <args>".format(lambda_addr, argv[0]))
        return

    # Run cmd on Lambda
    args = argv[1:]
    arg_str = " ".join(args)
    _, output = send_bash_command(arg_str, lambda_addr)

    if not output:
        print("[+] Error getting response from lambda at {}".format(lambda_addr))
        return
    print(output)


# cmd should be a string to pass to 'bash -c'
def send_bash_command(cmd, lambda_addr):
    bash_cmd = ["bash", "-c", cmd]
    return send_command(bash_cmd, lambda_addr)




if __name__ == "__main__":
    main()