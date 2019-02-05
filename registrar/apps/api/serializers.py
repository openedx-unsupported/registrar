"""
Serializers that can be shared across multiple versions of the API
should be created here. As the API evolves, serializers may become more
specific to a particular version of the API. In this case, the serializers
in question should be moved to versioned sub-package.
"""
from rest_framework import serializers


# pylint: disable=abstract-method
class ProgramSerializer(serializers.Serializer):
    """
    Serializer for the Program model.
    """
    discovery_uuid = serializers.CharField()
    title = serializers.CharField()


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
