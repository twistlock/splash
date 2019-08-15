#!/usr/bin/env python3

"""
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
"""


VALID_ATTRIBUTES = {    
    "HEADER" : '\033[95m',
    "BLUE" :'\033[94m',
    "GREEN" : '\033[92m',
    "WARNING" : '\033[93m',
    "FAIL" : '\033[91m',
    "BOLD" : '\033[1m',
    "UNDERLINE" : '\033[4m'
}

ENDC = '\033[0m' # signals attributes reset


START_NON_PRINT_IGNORE = "\001"
END_NON_PRINT_IGNORE = "\002"

# Formats a text according to given attributes
def colored(text, attributes):
	formated = text
	for attribute in attributes:
		if attribute in VALID_ATTRIBUTES:
			formated = VALID_ATTRIBUTES[attribute] + formated 
		else:
			raise KeyError("No such attribute '{}'".format(attribute))
	return formated + ENDC


def colored_for_input(text, attributes):
	formated = text
	for attribute in attributes:
		if attribute in VALID_ATTRIBUTES:
			formated = START_NON_PRINT_IGNORE + VALID_ATTRIBUTES[attribute] + END_NON_PRINT_IGNORE + formated 
		else:
			raise KeyError("No such attribute '{}'".format(attribute))
	return formated + START_NON_PRINT_IGNORE + ENDC + END_NON_PRINT_IGNORE



"""
For testing only
"""

if __name__ == "__main__":
	print("Testing mode (:")
	head = colored("zzz", ["HEADER"])
	print(list(head))
	print(head)