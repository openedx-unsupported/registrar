"""
Fake data for the mock API.
"""

from collections import namedtuple


FakeOrganization = namedtuple('FakeOrganization', [
    'key',
    'course_key_prefix',
    'metadata_readable',
    'enrollments_readable',
    'enrollments_writeable',
])

FakeProgram = namedtuple('FakeProgram', [
    'key',
    'managing_organization',
    'title',
    'url',
])


def _program(org, program_key, title):
    """
    Build a fake program.
    """
    return FakeProgram(
        program_key,
        org,
        title,
        'https://{}.edx.org/{}'.format(org.key, program_key),
    )


# List of fake organizations
FAKE_ORGS = [
    FakeOrganization('u-perezburgh', 'UPZx', False, False, False),
    FakeOrganization('brianchester-college', 'BCCx', True, False, False),
    FakeOrganization('donnaview-inst', 'DVIx', True, True, False),
    FakeOrganization('holmeshaven-polytech', 'HHPx', True, True, True),
]

# Dictionary mapping fake organization keys to fake organizations
FAKE_ORG_DICT = {org.key: org for org in FAKE_ORGS}

# List of fake program
FAKE_PROGRAMS = [
    _program(FAKE_ORGS[0], 'upz-masters-ancient-history', 'Master\'s in Ancient History'),
    _program(FAKE_ORGS[1], 'bcc-masters-english-lit', 'Master\'s in English Literature'),
    _program(FAKE_ORGS[2], 'dvi-masters-polysci', 'Master\'s in Political Science'),
    _program(FAKE_ORGS[2], 'dvi-mba', 'Master of Business Administration'),
    _program(FAKE_ORGS[3], 'hhp-masters-ce', 'Master\'s in Computer Engineering'),
    _program(FAKE_ORGS[3], 'hhp-masters-theo-physics', 'Master\'s in Theoretical Physics'),
    _program(FAKE_ORGS[3], 'hhp-masters-enviro', 'Master\'s in Environmental Science'),
]

# Dictionary mapping fake program keys to fake programs
FAKE_PROGRAM_DICT = {program.key: program for program in FAKE_PROGRAMS}

# Dictionary mapping fake orgazization keys to their fake programs
FAKE_ORG_PROGRAMS = {
    org.key: [
        program for program in FAKE_PROGRAMS
        if program.managing_organization.key == org.key
    ]
    for org in FAKE_ORGS
}
