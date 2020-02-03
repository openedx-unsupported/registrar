"""
@@TODO docstring
"""
from django.core.cache import cache

from registrar.apps.core.constants import (
    PROGRAM_CACHE_KEY_TPL,
    PROGRAM_CACHE_TIMEOUT,
    PROGRAM_DATA_LOAD_FAILED,
)


DISCOVERY_PROGRAM_API_TPL = 'api/v1/programs/{}/'


def get_program_discovery_data(program_uuid, client=None):
    """
    Get a JSON representation of a program from the Discovery service.

    Queries a cache with timeout of `PROGRAM_CACHE_TIMEOUT`
    before hitting Discovery.

    Returns `PROGRAM_DATA_LOAD_FAILED` if program is not found in Discovery.
    Note that the load-failed value will also be cached.

    Arguments:
        * program_uuid (UUID)
        * client (optional)

    Returns: dict|str
    """
    key = PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid)
    program_data = cache.get(key)
    if not isinstance(program, dict):
        program = _load_program_from_discovery(program_uuid, client)
        cache.set(key, program, PROGRAM_CACHE_TIMEOUT)
    return program_data


def _load_program_from_discovery(program_uuid, client=None):
    """
    Get a JSON representation of a program from the Discovery service.

    Returns `PROGRAM_DATA_LOAD_FAILED` if program is not found in Discovery.

    Arguments:
        * program_uuid (UUID)
        * client (optional)

    Returns:
        * dict if program exists in Discovery service.
        * `PROGRAM_DATA_LOAD_FAILED` otherwise.
    """
    url = urljoin(
        settings.DISCOVERY_BASE_URL, 'api/v1/programs/{}/'
    ).format(
        program_uuid
    )
    try:
        program_data = make_request('GET', url, client).json()
    except HTTPError:
        logger.exception(
            "Failed to load program with uuid %s from Discovery service.",
            program_uuid,
        )
        return PROGRAM_DATA_LOAD_FAILED
    return program_data
