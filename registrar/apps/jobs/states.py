""" States that a job can be in. """

PENDING = 'Pending'
IN_PROGRESS = 'In Progress'
SUCCEEDED = 'Succeeded'
FAILED = 'Failed'
RETRYING = 'Retrying'

ALL = [
    PENDING,
    IN_PROGRESS,
    SUCCEEDED,
    FAILED,
    RETRYING,
]
