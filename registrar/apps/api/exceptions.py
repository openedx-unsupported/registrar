"""
Custom exceptions extending those definined by DRF.
"""
from rest_framework.exceptions import APIException
from rest_framework import status
from registrar.apps.api.constants import ENROLLMENT_WRITE_MAX_SIZE


class EnrollmentPayloadTooLarge(APIException):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    default_detail = 'Enrollment limit {}'.format(ENROLLMENT_WRITE_MAX_SIZE)
    default_code = 'payload_too_large'
