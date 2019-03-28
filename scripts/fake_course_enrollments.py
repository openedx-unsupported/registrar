#!/usr/bin/python3
"""
Script to generate fake JSON result files for course enrollment GET endpoint.

The input to the script is the desired enrollment count and the file path of
a JSON program enrollment list. The output is a JSON list of a subset
input program enrollments.

Usage:
    python3 fake_course_enrollments.py <count> <program_enrollment_input_file>
Example:
    python3 fake_course_enrollments.py 25 pgm-enrolls.json
"""

import json
import sys
import random


# Map from program enrollment statuses to sets of possible course
# enrollment statuses.
STATUS_MAP = {
    'enrolled':
        {'enrolled', 'pending', 'withdrawn'},
    'enrolled-waiting':
        {'enrolled-waiting', 'pending-waiting'},
    'pending':
        {'pending', 'withdrawn'},
    'pending-waiting':
        {'pending-waiting'},
    'suspended':
        {'enrolled', 'pending', 'withdrawn'},
    'canceled':
        {'withdrawn'},
}


def main(args):
    """
    Main function.

    Arguments:
        args (list[str]): Command-line args excluding script name.

    Returns: int
        Exit code
    """
    help_text = (
        'Usage: python fake_course_enrollments.py ' +
        '<count> <program_enrollment_input_file>'
    )
    if len(args) !=2:
        print(help_text)
        return 1
    try:
        count = int(args[0])
    except ValueError:
        print(help_text)
        return 1
    enrolls = generate_fake_enrollments(count, args[1])
    print(json.dumps(enrolls, indent=4))
    return 0


def generate_fake_enrollments(count, in_path):
    """
    Generate fake course enrollment list.

    Arguments:
        count (int): number of enrollment dicts to generate
        in_path (str): file path to draw program enrollments from

    Returns: list[dict]
    """
    with open(in_path) as f:
        text = f.read()
    program_enrollments = json.loads(text)
    course_enrollments = random.sample(program_enrollments, count)
    for enrollment in course_enrollments:
        status_choices = list(STATUS_MAP[enrollment['status']])
        enrollment['status'] = random.choice(status_choices)
    return course_enrollments


exit(main(sys.argv[1:]))
