"""
Interface for fetching catalog data from the Discovery service
with a temporary cache.
"""
import logging
from posixpath import join as urljoin

from django.conf import settings
from django.core.cache import cache
from requests.exceptions import HTTPError

from .rest_utils import make_request


logger = logging.getLogger(__name__)

DISCOVERY_PROGRAM_API_TPL = 'api/v1/programs/{}/'
PROGRAM_CACHE_KEY_TPL = 'program-data:{uuid}'
PROGRAM_CACHE_TIMEOUT = 120


def get_program_data(program_uuid, client=None):
    """
    Get a JSON representation of a program from the Discovery service.

    Returns None if not found.

    Queries a cache with timeout of `PROGRAM_CACHE_TIMEOUT`
    before hitting Discovery to load the authoritative data.
    Note that the "not-foundeness" of programs will also be cached.
    For example:
    * Program X is requested.
    * It is not found in Discovery. This result is cached.
    * Before PROGRAM_CACHE_TIMEOUT has passed, Program X is created
      in Discovery.
    * Program X will not be loaded from Discovery until PROGRAM_CACHE_TIMEOUT
      has passed.

    Arguments:
        * program_uuid (UUID)
        * client (optional)

    Returns: dict|None
    """
    # When caching, we need to translate `None` (i.e. not found in Discovery)
    # to a sentinel string, otherwise we will not be able to tell
    # "not in cache" apart from "cached as not in Discovery".
    PROGRAM_DATA_LOAD_FAILED = 'PROGRAM-LOAD-FROM-DISCOVERY-FAILED'

    key = PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid)
    program_data = cache.get(key)
    if isinstance(program_data, dict):
        return program_data
    elif program_data == PROGRAM_DATA_LOAD_FAILED:
        return None

    disco_program = _load_from_discovery(program_uuid, client)
    cache_value = disco_program if disco_program else PROGRAM_DATA_LOAD_FAILED
    cache.set(key, cache_value, PROGRAM_CACHE_TIMEOUT)
    return disco_program


def clear_program_data(program_uuids):
    """
    Manually clear data in Discovery cache for a set of programs.

    Arguments:
        program_uuids (list[UUID|str])
    """
    cache.delete_many([
        PROGRAM_CACHE_KEY_TPL.format(uuid=uuid) for uuid in program_uuids
    ])


def _load_from_discovery(program_uuid, client=None):
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
        settings.DISCOVERY_BASE_URL,
        DISCOVERY_PROGRAM_API_TPL.format(program_uuid)
    )
    try:
        return make_request('GET', url, client).json()
    except HTTPError:
        logger.exception(
            "Failed to load program with uuid %s from Discovery service.",
            program_uuid,
        )
        return None
