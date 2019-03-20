"""
Fake data for the mock API.
"""

from collections import namedtuple

from registrar.apps.core.utils import name_to_key


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

FakeCourseRun = namedtuple('FakeCourseRun', [
    'key',
    'title',
    'marketing_url',
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


def _course_run(title, org, course, run="Spring2050"):
    """
    Build a fake course.
    """
    return FakeCourseRun(
        'course-v1:{}+{}+{}'.format(org, course, run),
        title,
        'https://www.edx.org/fake-course/{}'.format(name_to_key(title)),
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

# List of fake course runs
FAKE_COURSE_RUNS = [
    _course_run('Ancient History 101', 'UPZx', 'HIST-101'),
    _course_run('Literature', 'BCCx', 'EN-111'),
    _course_run('Classics', 'BCCx', 'EN-121'),
    _course_run('Poetry', 'BCCx', 'EN-131'),
    _course_run('Poetry', 'BCCx', 'EN-131', run='Fall2050'),
    _course_run('Communication 101', 'DVIx', 'COMM-101'),
    _course_run('History of Democracy', 'DVIx', 'GOV-200'),
    _course_run('International Law', 'DVIx', 'GOV-201'),
    _course_run('US Constitutional Law', 'DVIx', 'GOV-202'),
    _course_run('Modern Management Practices', 'DVIx', 'BIZ-200'),
    _course_run('Introduction to Calculus', 'HHPx', 'MA-101'),
    _course_run('Multivariable Calculus', 'HHPx', 'MA-102', run='Fall2050'),
    _course_run('Signal Processing', 'HHPx', 'CE-300'),
    _course_run('Signal Processing', 'HHPx', 'CE-300', run='Summer2050'),
    _course_run('Waves and Oscillations', 'HHPx', 'PHYS-260'),
]

# Dictionary mapping fake course run keys to fake course runs
FAKE_COURSE_RUN_DICT = {course_run.key: course_run for course_run in FAKE_COURSE_RUNS}

# Dictionary mapping fake program keys to their fake course run keys, sans
# the 'course-v1:' prefix
_FAKE_PROGRAM_COURSE_RUN_KEY_BODIES = {
    'upz-masters-ancient-history': [
        'UPZx+HIST-101+Spring2050',
    ],
    'bcc-masters-english-lit': [
        'BCCx+EN-111+Spring2050',
        'BCCx+EN-121+Spring2050',
        'BCCx+EN-131+Fall2050',
        'BCCx+EN-131+Spring2050',
    ],
    'dvi-masters-polysci': [
        'DVIx+COMM-101+Spring2050',
        'DVIx+GOV-200+Spring2050',
        'DVIx+GOV-201+Spring2050',
        'DVIx+GOV-202+Spring2050',
    ],
    'dvi-mba': [
        'DVIx+COMM-101+Spring2050',
        'DVIx+BIZ-200+Spring2050',
    ],
    'hhp-masters-ce': [
        'HHPx+MA-101+Spring2050',
        'HHPx+MA-102+Fall2050',
        'HHPx+CE-300+Spring2050',
        'HHPx+CE-300+Summer2050',
    ],
    'hhp-masters-theo-physics': [
        'HHPx+MA-101+Spring2050',
        'HHPx+MA-102+Fall2050',
        'HHPx+PHYS-260+Spring2050',
    ],
    'hhp-masters-enviro': [],  # Purposefully empty, to test empty program case
}

# Dictionary mapping fake proram keys to their fake course runs
FAKE_PROGRAM_COURSE_RUNS = {
    program_key: [
        FAKE_COURSE_RUN_DICT['course-v1:' + course_run_key]
        for course_run_key in course_run_keys
    ]
    for program_key, course_run_keys
    in _FAKE_PROGRAM_COURSE_RUN_KEY_BODIES.items()
}
