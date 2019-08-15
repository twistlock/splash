#!/usr/bin/env python3

VALID_ATTRIBUTES = {
	"HEADER" : '\001\033[95m\002',
    "BLUE" :'\001\033[94m\002',
    "GREEN" : '\001\033[92m\002',
    "WARNING" : '\001\033[93m\002',
    "FAIL" : '\001\033[91m\002',
    "BOLD" : '\001\033[1m\002',
    "UNDERLINE" : '\001\033[4m\002'
}

ENDC = '\001\033[0m\002' # signals attributes reset


# Formats a text according to given attributes
def colored(text, attributes):
	formated = text
	for attribute in attributes:
		if attribute in VALID_ATTRIBUTES:
			formated = VALID_ATTRIBUTES[attribute] + formated 
		else:
			raise KeyError("No such attribute '{}'".format(attribute))
	return formated + ENDC





"""
For testing only
"""

if __name__ == "__main__":
	print("Testing mode (:")
	head = colored("zzz", ["HEADER"])
	print(list(head))
	print(head)