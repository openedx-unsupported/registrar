"""
Simple interface to program details from Course Discovery data through a volatile cache.
"""
import logging
from collections import namedtuple
from uuid import UUID

from django.conf import settings
from django.core.cache import cache

from .api_client import DiscoveryServiceClient
from .constants import PROGRAM_CACHE_KEY_TPL


logger = logging.getLogger(__name__)

DiscoveryCourseRun = namedtuple(
    'DiscoveryCourseRun',
    ['key', 'external_key', 'title', 'marketing_url'],
)


class ProgramDetails:
    """
    Details about a program from the Course Discovery service.

    Data from Discovery is cached for `settings.PROGRAM_CACHE_TIMEOUT` seconds.

    If Discovery data cannot be loaded, we quietly fall back to an object that returns
    default values (generally empty dicts and None) instead of raising an exception.
    Callers should anticipate that Discovery data may not always be available,
    and use the default values gracefully.

    Details are loaded in the call to the constructor.

    Example usage:
        details = ProgramDetails(program.discovery_uuid)
        if details.find_course_run(course_key):
            # ...
    """

    def __init__(self, uuid):
        """
        Initialize a program details instance and load details from cache or Discovery.

        Arguments:
            uuid (UUID|str): UUID of the program as defined in Discovery service.
        """
        self.uuid = uuid
        self.raw_data = self.get_raw_data_for_program(uuid)

    @classmethod
    def get_raw_data_for_program(cls, uuid):
        """
        Retrieve JSON data containing program details, looking in cache first.

        This is the access point to the "Discovery cache" as referenced
        in comments throughout Registrar.

        Note that "not-found-in-discovery" is purposefully cached as `{}`,
        whereas `cache.get(key)` will return `None` if the key is not in the
        cache.

        Arguments:
            uuid (UUID|str): UUID of the program as defined in Discovery service.

        Returns: dict
        """
        cache_key = PROGRAM_CACHE_KEY_TPL.format(uuid=uuid)
        data = cache.get(cache_key)
        if not isinstance(data, dict):
            data = DiscoveryServiceClient.get_program(uuid)
            if not isinstance(data, dict):
                data = {}
            cache.set(cache_key, data, settings.PROGRAM_CACHE_TIMEOUT)
        return data

    @classmethod
    def clear_cache_for_programs(cls, program_uuids):
        """
        Clear any details from Discovery that we have cached for the given programs.

        Arguments:
            program_uuids (Iterable[str|UUID])
        """
        cache_keys_to_delete = [
            PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid)
            for program_uuid in program_uuids
        ]
        cache.delete_many(cache_keys_to_delete)

    @classmethod
    def load_many(cls, uuids):
        """
        Given program UUIDs, load a dict of ProgramDetail instances, keyed by UUID.

        TODO MST-266:
        This is currently no more efficient than loading the details one-by-one.
        For programs that aren't in the cache, we ought to load them in a single
        API call to Course Disocovery.

        Arguments:
            uuids (Iterable[str|UUID]): Program UUIDs.

        Returns: dict[(str|UUID): Program]
        """
        return {
            uuid: ProgramDetails(uuid) for uuid in uuids
        }

    @property
    def title(self):
        """
        Return title of program.

        Falls back to None if unavailable.
        """
        return self.raw_data.get('title')

    @property
    def url(self):
        """
        Return URL of program

        Falls back to None if unavailable.
        """
        return self.raw_data.get('marketing_url')

    @property
    def program_type(self):
        """
        Return type of the program ("Masters", "MicroMasters", etc.).

        Falls back to None if unavailable.
        """
        return self.raw_data.get('type')

    @property
    def is_enrollment_enabled(self):
        """
        Return whether enrollment is enabled for this program.

        Falls back to False if required data unavailable.

        Currently, enrollment is enabled if and only if the program is a Master's
        degree. This may change in the future.
        """
        return self.program_type == 'Masters'

    @property
    def active_curriculum_details(self):
        """
        Return dict containing details for active curriculum.

        TODO:
        We define 'active' curriculum as the first one in the list of
        curricula where is_active is True.
        This is a temporary assumption, originally made in March 2019.
        We expect that future programs may have more than one curriculum
        active simultaneously, which will require modifying the API.

        Falls back to empty dict if no active curriculum or if data unavailable.
        """
        try:
            return next(
                c for c in self.raw_data.get('curricula', [])
                if c.get('is_active')
            )
        except StopIteration:
            logger.exception(
                'Discovery API returned no active curricula for program %s',
                self.uuid,
            )
            return {}

    @property
    def active_curriculum_uuid(self):
        """
        Get UUID string of active curriculum, or None if no active curriculum.

        See `active_curriculum_details` docstring for more details.
        """
        try:
            return UUID(self.active_curriculum_details.get('uuid'))
        except (TypeError, ValueError):
            return None

    @property
    def course_runs(self):
        """
        Get list of DiscoveryCourseRuns defined in root of active curriculum.

        TODO:
        In March 2019 we made a temporary assumption that the curriculum
        does not contain nested programs.
        We expect that this will need revisiting eventually,
        as future programs may have more than one curriculum.

        Also see `active_curriculum_details` docstring details on how the 'active'
        curriculum is determined.

        Falls back to empty list if no active curriculum or if data unavailable.
        """
        return [
            DiscoveryCourseRun(
                key=course_run.get("key"),
                external_key=course_run.get("external_key"),
                title=course_run.get("title"),
                marketing_url=course_run.get("marketing_url"),
            )
            for course in self.active_curriculum_details.get("courses", [])
            for course_run in course.get("course_runs", [])
        ]

    def find_course_run(self, course_id):
        """
        Given a course id, return the course_run with that `key` or `external_key`

        Returns None if course run is not found in the cached program.
        """
        try:
            return next(
                course_run for course_run in self.course_runs
                if course_id in {course_run.key, course_run.external_key}
            )
        except StopIteration:
            return None

    def get_external_course_key(self, course_id):
        """
        Given a course ID, return the external course key for that course_run.
        The course key passed in may be an external or internal course key.

        Returns None if course run is not found in the cached program.
        """
        course_run = self.find_course_run(course_id)
        if course_run:
            return course_run.external_key
        return None

    def get_course_key(self, course_id):
        """
        Given a course ID, return the internal course ID for that course run.
        The course ID passed in may be an external or internal course key.

        Returns None if course run is not found in the cached program.
        """
        course_run = self.find_course_run(course_id)
        if course_run:
            return course_run.key
        return None
