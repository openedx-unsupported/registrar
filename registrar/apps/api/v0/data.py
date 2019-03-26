"""
Fake data for the mock API.
"""

from collections import namedtuple
from datetime import datetime
import random
import uuid

from django.core.cache import cache
from user_tasks.models import UserTaskStatus

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

FakeJobAcceptance = namedtuple('FakeJobAcceptance', [
    'job_id',
    'job_url',
])

# Info about the invokation of job. Stored in the cache.
_FakeJobInfo = namedtuple('_FakeJobInfo', [
    'original_url',
    'created',
    'duration_seconds',
    'result_filename',  # None indicates task should fail after duration_seconds
])

FakeJobStatus = namedtuple('FakeJobStatus', [
    'job_id',
    'original_url',
    'created',
    'state',
    'result',
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


_FAKE_JOB_CACHE_PREFIX = 'api-v0-job:'
_FAKE_JOB_CACHE_LIFETIME = 60 * 60 * 24  # Clean up jobs after one day


# Dictionary mapping fake program keys to their fake enrollment listing filenames.
# None indicates that the job should fail and not have a result.
_FAKE_JOB_RESULT_FILENAMES_BY_PROGRAM = {
    'dvi-masters-polysci': 'polysci.json',
    'dvi-mba': 'mba.json',
    'hhp-masters-ce': 'ce.json',
    'hhp-masters-theo-physics': 'physics.json',
    'hhp-masters-enviro': None,
}


def invoke_fake_program_enrollment_listing_job(
        program_key,
        original_url,
        min_duration=5,
        max_duration=5
):
    """
    Create fake enrollment listing job for program with the given key.

    Info about the "invocation" of the job gets added to the cache,
    retrievable by ``get_fake_job_status``. After a random number of seconds
    between ``min_duration`` and ``max_duration``, ``get_fake_job_status``
    will return the job as Succeeded (with a result URL) or Failed.

    Arguments:
        program_key (str)
        original_url (str): original URL of the request
        min_duration (int): inclusive lower bound for number of seconds job
            should appear as 'In Progress'
        max_duration (int): inclusive upper bound for number of seconds job
            should appear as 'In Progress'

    Returns: str
        UUID of the created job
    """
    job_id = str(uuid.uuid4())
    created = datetime.now()
    duration_seconds = random.randrange(min_duration, max_duration + 1)
    result_filename = _FAKE_JOB_RESULT_FILENAMES_BY_PROGRAM[program_key]
    job_info = _FakeJobInfo(
        original_url, created, duration_seconds, result_filename,
    )
    cache_key = _FAKE_JOB_CACHE_PREFIX + job_id
    cache.set(cache_key, job_info, _FAKE_JOB_CACHE_LIFETIME)
    return job_id


def get_fake_job_status(job_id, to_absolute_uri):
    """
    Get status of fake job.

    We try to load the job, returning None if it does not exist.
    If it does, we construct a FakeJobStatus to return.

    If the job's duration has elapsed since its creation, then the
    state of the job will be Failed or Succeeded. Otherwise, it will be
    In Progress.

    Arguments:
        job_id (str): UUID of job
        to_absolute_uri (str -> str): function that converts a path to a
            complete URL. We must take this as an argument because there is
            no such library function available outside the context of a Request.

    Returns: FakeJobStatus|NoneType
    """
    cache_key = _FAKE_JOB_CACHE_PREFIX + job_id
    job_info = cache.get(cache_key)
    if not job_info:
        return None

    result = None

    elapsed = datetime.now() - job_info.created
    if elapsed.seconds < job_info.duration_seconds:
        state = UserTaskStatus.IN_PROGRESS
    elif not job_info.result_filename:
        state = UserTaskStatus.FAILED
    else:
        state = UserTaskStatus.SUCCEEDED
        path = '/static/api/v0/program-enrollments/{}'.format(
            job_info.result_filename
        )
        result = to_absolute_uri(path)

    return FakeJobStatus(
        job_id, job_info.original_url, job_info.created, state, result,
    )
