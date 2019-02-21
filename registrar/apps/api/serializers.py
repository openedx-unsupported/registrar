"""
Serializers that can be shared across multiple versions of the API
should be created here. As the API evolves, serializers may become more
specific to a particular version of the API. In this case, the serializers
in question should be moved to versioned sub-package.
"""
from rest_framework import serializers

from registrar.apps.enrollments.models import Program


# pylint: disable=abstract-method
class ProgramSerializer(serializers.ModelSerializer):
    """
    Serializer for Programs.
    """
    program_id = serializers.CharField(source='key')
    program_title = serializers.CharField(source='title')

    class Meta:
        model = Program
        fields = ('program_id', 'program_title')


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
