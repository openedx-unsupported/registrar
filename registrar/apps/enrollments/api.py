"""
The API through which enrollment models should be operated on.
"""
from registrar.apps.enrollments.models import (
    Learner,
    LearnerProgramEnrollment,
    Program,
)


def get_learner_by_email(email):
    """
    Given an email address, returns a corresponding Learner,
    or None if no such learner exists.
    """
    try:
        return Learner.objects.get(email=email)
    except Learner.DoesNotExist:
        return None


def update_or_create_learner(email, **kwargs):
    """
    Given an email and optional other ids, creates or updates
    a learner record.  Returns a tuple of (learner, was_created).
    """
    allowed_fields = {'lms_id', 'external_id'}
    defaults = _defaults_from_allowed_fields(kwargs, allowed_fields)
    return Learner.objects.update_or_create(email=email, defaults=defaults)


def get_program_by_uuid(discovery_uuid):
    """
    Given a program UUID (as specified in the discovery service),
    returns a corresponding Program object, or None
    if no such program exists.
    """
    try:
        return Program.objects.get(discovery_uuid=discovery_uuid)
    except Program.DoesNotExist:
        return None


def update_or_create_program(discovery_uuid, **kwargs):
    """
    Given a program UUID (as specified in the discovery service),
    updates or creates a program with that UUID
    with the provided kwargs.
    """
    Program.objects.update_or_create(discovery_uuid=discovery_uuid, defaults=kwargs)


def enroll_in_program(learner, program, **kwargs):
    """
    Given a learner object and program object, create
    or update an enrollment record indicating that the learner
    is enrolled in the program.
    Returns a tuple of (enrollment, was_created).
    """
    defaults = _defaults_from_allowed_fields(kwargs, {'status'})
    return LearnerProgramEnrollment.objects.update_or_create(
        learner=learner,
        program=program,
        defaults=defaults
    )


def _defaults_from_allowed_fields(kwargs, allowed_fields):
    """
    Helper method for creating defaults in update_or_create() calls.
    """
    return {
        field: kwargs[field]
        for field in kwargs
        if field in allowed_fields
    }
