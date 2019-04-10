"""
Serializers that can be shared across multiple versions of the API
should be created here. As the API evolves, serializers may become more
specific to a particular version of the API. In this case, the serializers
in question should be moved to versioned sub-package.
"""
from rest_framework import serializers

from registrar.apps.enrollments.models import Program
from registrar.apps.jobs.states import ALL as JOB_STATES


# pylint: disable=abstract-method
class ProgramSerializer(serializers.ModelSerializer):
    """
    Serializer for Programs.
    """
    program_key = serializers.CharField(source='key')
    program_title = serializers.CharField(source='title')
    program_url = serializers.URLField(source='url')

    class Meta:
        model = Program
        fields = ('program_key', 'program_title', 'program_url')


class LearnerSerializer(serializers.Serializer):
    """
    Serializer for the Learner model.
    """
    id = serializers.IntegerField()
    lms_id = serializers.IntegerField()
    email = serializers.CharField()
    external_id = serializers.CharField()
    status = serializers.CharField()


class LearnerProgramEnrollmentSerializer(serializers.Serializer):
    """
    Serializer for the LearnerProgramEnrollment model.
    """
    learner = LearnerSerializer()
    program = ProgramSerializer()
    status = serializers.CharField()


class ProgramEnrollmentRequestSerializer(serializers.Serializer):
    """
    Serializer for request to create a LearnerProgramEnrollment
    """
    STATUS_CHOICES = ['pending', 'enrolled']

    student_key = serializers.CharField(allow_blank=False)
    email = serializers.CharField(allow_blank=False)
    status = serializers.ChoiceField(allow_blank=False, choices=STATUS_CHOICES)


class ProgramEnrollmentModificationRequestSerializer(serializers.Serializer):
    """
    Serializer for request to modify a LearnerProgramEnrollment
    """
    STATUS_CHOICES = ['pending', 'enrolled', 'suspended', 'canceled']

    student_key = serializers.CharField(allow_blank=False)
    status = serializers.ChoiceField(allow_blank=False, choices=STATUS_CHOICES)


class CourseEnrollmentRequestSerializer(serializers.Serializer):
    """
    Serializer for a request to create a LearnerCourseEnrollment
    """
    STATUS_CHOICES = ['pending', 'enrolled']

    student_key = serializers.CharField(allow_blank=False)
    status = serializers.ChoiceField(allow_blank=False, choices=STATUS_CHOICES)


class CourseEnrollmentModificationRequestSerializer(serializers.Serializer):
    """
    Serializer for a request to modify a LearnerCourseEnrollment
    """
    STATUS_CHOICES = ['pending', 'enrolled', 'withdrawn']

    student_key = serializers.CharField(allow_blank=False)
    status = serializers.ChoiceField(allow_blank=False, choices=STATUS_CHOICES)


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


class JobSerializer(serializers.Serializer):
    """
    Serializer for data about the status of a job.
    """
    original_url = serializers.URLField()
    created = serializers.DateTimeField()
    state = serializers.ChoiceField(allow_blank=False, choices=JOB_STATES)
    result = serializers.URLField(allow_null=True)
