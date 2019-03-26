#!/usr/bin/python3
"""
Script to generate fake JSON result files for program enrollment GET endpoint.

Usage:
    python3 fake_program_enrollments.py <count> <student_key_length> <email_domain>
Example:
    python3 fake_program_enrollments.py 100 10 example.edu

Requires Python 3 and Faker.

Note: This breaks if ``student_key_length`` exceeds 18.
"""

import json
import sys
import random

from faker import Faker


fake = Faker()


STATUS_CHOICES = {
    'enrolled',
    'enrolled-waiting',
    'pending',
    'pending-waiting',
    'suspended',
    'canceled',
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
        'Usage: python fake_program_enrollments.py ' +
        '<count> <student_key_length> <email_domain>'
    )
    if len(args) != 3:
        print(help_text)
        return 1
    try:
        count = int(args[0])
        key_length = int(args[1])
    except ValueError:
        print(help_text)
        return 1
    enrolls = generate_fake_enrollments(count, key_length, args[2])
    print(json.dumps(enrolls, indent=4))
    return 0


def generate_fake_enrollments(count, key_length, email_domain):
    """
    Generate fake program enrollment list.

    Arguments:
        count (int): number of enrollment dicts to generate
        key_length (int): number of digits for student keys
        email_domain (str): domain for student emails

    Returns: list[dict]
    """
    field_lists = {}

    key_space = range(10 ** key_length)
    key_numbers = random.sample(key_space, count)
    field_lists['student_key'] = [str(n).zfill(key_length) for n in key_numbers]

    emails = set()
    while len(emails) < count:
        emails.add(generate_fake_email(email_domain))
    field_lists['email'] = list(emails)

    choices = list(STATUS_CHOICES)
    field_lists['status'] = [random.choice(choices) for _ in range(count)]

    return [
        {key: values[i] for key, values in field_lists.items()}
        for i in range(count)
    ]


def generate_fake_email(email_domain):
    """
    Generate a fake email address.

    Args:
        email_domain (str): the part of the email after the @

    Returns: str
    """
    return '{}{}@{}'.format(
        fake.first_name()[0], fake.last_name(), email_domain,
    ).lower()


if __name__ == '__main__':
    exit(main(sys.argv[1:]))
