"""
The public-facing REST API.
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from registrar.apps.enrollments.models import LearnerProgramEnrollment
from registrar.apps.api.serializers import LearnerProgramEnrollmentSerializer


class ProgramEnrollmentView(APIView):
    def get(self, request, discovery_uuid=None, learner_id=None):
        if discovery_uuid:
            enrollments = LearnerProgramEnrollment.objects.filter(program__discovery_uuid=discovery_uuid)
            return Response(LearnerProgramEnrollmentSerializer(enrollments, many=True).data)
