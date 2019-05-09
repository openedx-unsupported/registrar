"""
Serializers that can be shared across multiple versions of the API
should be created here. As the API evolves, serializers may become more
specific to a particular version of the API. In this case, the serializers
in question should be moved to versioned sub-package.
"""
from rest_framework import serializers
from user_tasks.models import UserTaskStatus

from registrar.apps.enrollments.constants import (
    COURSE_ENROLLMENT_STATUSES,
    PROGRAM_ENROLLMENT_STATUSES,
)
from registrar.apps.enrollments.models import Program


# pylint: disable=abstract-method
class ProgramSerializer(serializers.ModelSerializer):
    """
    Serializer for Programs.
    """
    program_key = serializers.CharField(source='key')

    class Meta:
        model = Program
        fields = ('program_key',)


class ProgramEnrollmentRequestSerializer(serializers.Serializer):
    """
    Serializer for request to create a program enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)


class ProgramEnrollmentModificationRequestSerializer(serializers.Serializer):
    """
    Serializer for request to modify a program enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=PROGRAM_ENROLLMENT_STATUSES)


class CourseEnrollmentRequestSerializer(serializers.Serializer):
    """
    Serializer for a request to create a course enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)


class CourseEnrollmentModificationRequestSerializer(serializers.Serializer):
    """
    Serializer for a request to modify a course enrollment
    """
    student_key = serializers.CharField()
    status = serializers.ChoiceField(choices=COURSE_ENROLLMENT_STATUSES)


class CourseRunSerializer(serializers.Serializer):
    """
    Serializer for a course run returned from the
    Course Discovery Service
    """
    course_id = serializers.CharField(source='key')
    course_title = serializers.CharField(source='title')
    course_url = serializers.URLField(source='marketing_url')


class JobAcceptanceSerializer(serializers.Serializer):
    """
    Serializer for data about the invocation of a job.
    """
    job_id = serializers.UUIDField()
    job_url = serializers.URLField()


class JobStatusSerializer(serializers.Serializer):
    """
    Serializer for data about the status of a job.
    """
    STATUS_CHOICES = {
        UserTaskStatus.PENDING,
        UserTaskStatus.IN_PROGRESS,
        UserTaskStatus.SUCCEEDED,
        UserTaskStatus.FAILED,
        UserTaskStatus.RETRYING,
    }

    created = serializers.DateTimeField()
    state = serializers.ChoiceField(choices=STATUS_CHOICES)
    result = serializers.URLField(allow_null=True)
