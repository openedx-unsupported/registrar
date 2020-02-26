"""
Proxies that wrap Django models and enrich their functionality.
"""
import logging
from collections import namedtuple
from posixpath import join as urljoin
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from requests.exceptions import HTTPError

from .constants import PROGRAM_CACHE_KEY_TPL, PROGRAM_CACHE_TIMEOUT
from .models import Program
from .rest_utils import make_request


logger = logging.getLogger(__name__)
DISCOVERY_PROGRAM_API_TPL = 'api/v1/programs/{}/'

DiscoveryCourseRun = namedtuple(
    'DiscoveryCourseRun',
    ['key', 'external_key', 'title', 'marketing_url'],
)


class DiscoveryProgram(Program):
    """
    Proxy to Program model that is enriched with details available from Discovery service.

    Data from Discovery is cached for `PROGRAM_CACHE_TIMEOUT` seconds.
    If Discovery data cannot be loaded, we fall back to default values.

    Get an instance of this class just like you would an instance of `Program`:
        DiscoveryProgram.objects.get(discovery_uuid=YOUR_UUID)

    Or, if you just want the raw JSON instead of a model instance:
        DiscoveryProgram.get_program_details(YOUR_UUID)

    To patch Discovery-data-loading in tests, patch `get_program_details`.
    """
    class Meta:
        # Guarantees that a table will not be created for this proxy model.
        proxy = True

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        When DiscoveryProgram is loaded, warm the cache.

        This way, errors are surfaced right upon `DiscoveryProgram.objects.get`
        instead of during attribute access.

        Overrides `Model.from_db`.
        """
        instance = super().from_db(db, field_names, values)
        cls.get_program_details(instance.discovery_uuid)  # pylint: disable=no-member
        return instance

    @classmethod
    def get_program_details(cls, program_uuid):
        """
        Get a JSON representation of a program from the Discovery service.

        Returns an empty dict if not found or other HTTP error.

        Queries a cache with timeout of `PROGRAM_CACHE_TIMEOUT`
        before hitting Discovery to load the authoritative data.

        Note that the "not-founded-ness" of programs will also be cached
        using an empty dictionary (which is distinct from None).

        For example:
            * Program X is requested.
            * It is not found in Discovery. This result is cached as `{}`
            * Before PROGRAM_CACHE_TIMEOUT has passed, Program X is created
              in Discovery.
            * Program X will not be loaded from Discovery until PROGRAM_CACHE_TIMEOUT
              has passed.

        Arguments:
            * program_uuid (UUID)

        Returns: dict
        """
        key = PROGRAM_CACHE_KEY_TPL.format(uuid=program_uuid)
        # Note that "not-found-in-discovery" is purposefully cached as `{}`,
        # whereas `cache.get(key)` will return `None` if the key is not in the
        # cache.
        program_details = cache.get(key)
        if not isinstance(program_details, dict):
            program_details = cls._fetch_discovery_program_details(program_uuid)
            cache_value = program_details if isinstance(program_details, dict) else {}
            cache.set(key, cache_value, PROGRAM_CACHE_TIMEOUT)
        return program_details

    @classmethod
    def clear_cached_program_details(cls, program_uuids):
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

    @staticmethod
    def _fetch_discovery_program_details(program_uuid):
        """
        Fetch a JSON representation of a program from the Discovery service.

        Returns None if not found or other HTTP error.

        Arguments:
            * program_uuid (UUID)
            * client (optional)

        Returns: dict|None
        """
        url = urljoin(
            settings.DISCOVERY_BASE_URL,
            DISCOVERY_PROGRAM_API_TPL.format(program_uuid)
        )
        try:
            return make_request('GET', url, client=None).json()
        except HTTPError:
            logger.exception(
                "Failed to load program with uuid %s from Discovery service.",
                program_uuid,
            )
            return None

    @property
    def discovery_details(self):
        """
        Get cached program details from Discovery.

        Returns empty dict if details could not be loaded from Discovery
        due to a 404 response or some other issue.

        Returns: JSON dict
        """
        return self.get_program_details(self.discovery_uuid)

    @property
    def title(self):
        """
        Return title of program.

        Falls back to program key if unavailable.
        """
        return self.discovery_details.get('title', self.key)

    @property
    def url(self):
        """
        Return URL of program

        Falls back to None if unavailable.
        """
        return self.discovery_details.get('marketing_url')

    @property
    def program_type(self):
        """
        Return type of the program ("Masters", "MicroMasters", etc.).

        Falls back to None if unavailable.
        """
        return self.discovery_details.get('type')

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
                c for c in self.discovery_details.get('curricula', [])
                if c.get('is_active')
            )
        except StopIteration:
            logger.exception(
                'Discovery API returned no active curricula for program {}'.format(
                    self.discovery_uuid
                )
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
