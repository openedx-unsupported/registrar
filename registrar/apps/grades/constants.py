""" Constants for the grades app """
from enum import Enum


class GradeReadStatus(Enum):
    OK = 200
    NO_CONTENT = 204
    MULTI_STATUS = 207
    UNPROCESSABLE_ENTITY = 422
