"""
Serializers that can be shared across multiple versions of the API
should be created here. As the API evolves, serializers may become more
specific to a particular version of the API. In this case, the serializers
in question should be moved to versioned sub-package.
"""
from rest_framework import serializers
from user_tasks.models import UserTaskStatus


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
