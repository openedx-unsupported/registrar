"""
Test for common data functions
"""
import uuid
from datetime import datetime
from posixpath import join as urljoin

import ddt
import mock
import responses
from django.conf import settings
from django.core.cache import cache
from django.http import Http404
from django.test import TestCase
from requests.exceptions import HTTPError

from ..data import (
    DISCOVERY_PROGRAM_API_TPL,
    DiscoveryCourseRun,
    DiscoveryProgram,
)
from .utils import mock_oauth_login


class GetDiscoveryProgramTestCase(TestCase):
    """ Test get_discovery_program function """
    program_uuid = str(uuid.uuid4())
    curriculum_uuid = str(uuid.uuid4())
    discovery_url = urljoin(settings.DISCOVERY_BASE_URL, DISCOVERY_PROGRAM_API_TPL.format(program_uuid))
    course_run_1 = {
        'key': '0001',
        'uuid': '0000-0001',
        'title': 'Test Course 1',
        'external_key': 'testorg-course-101',
        'marketing_url': 'https://stem-institute.edx.org/masters-in-cs/test-course-1',
    }
    program_title = "Master's in CS"
    program_url = 'https://stem-institute.edx.org/masters-in-cs'
    program_type = "Masters"
    programs_response = {
        'title': program_title,
        'marketing_url': program_url,
        'type': program_type,
        'curricula': [{
            'uuid': curriculum_uuid,
            'is_active': True,
            'courses': [{'course_runs': [course_run_1]}],
        }],
    }
    expected_program = DiscoveryProgram(
        version=0,
        loaded=datetime.now(),
        uuid=program_uuid,
        title=program_title,
        url=program_url,
        program_type=program_type,
        active_curriculum_uuid=curriculum_uuid,
        course_runs=[
            DiscoveryCourseRun(
                course_run_1['key'],
                course_run_1['external_key'],
                course_run_1['title'],
                course_run_1['marketing_url'],
            ),
        ],
    )

    def setUp(self):
        super().setUp()
        cache.clear()

    def assert_discovery_programs_equal(self, this_program, that_program):
        """ Asserts DiscoveryProgram equality, ignoring `loaded` field. """
        self.assertEqual(this_program.version, 1)
        self.assertEqual(this_program.uuid, that_program.uuid)
        self.assertEqual(this_program.title, that_program.title)
        self.assertEqual(this_program.url, that_program.url)
        self.assertEqual(this_program.program_type, that_program.program_type)
        self.assertEqual(this_program.active_curriculum_uuid, that_program.active_curriculum_uuid)
        self.assertEqual(this_program.course_runs, that_program.course_runs)

    @mock_oauth_login
    @responses.activate
    def test_get_discovery_program_success(self):
        """
        Verify initial call returns data from the discovery service and additional function
        calls return from cache.

        Note: TWO calls are initially made to discovery in order to obtain an auth token and then
        request data.
        """
        responses.add(
            responses.GET,
            self.discovery_url,
            json=self.programs_response,
            status=200
        )
        loaded_program = DiscoveryProgram.get(self.program_uuid)
        self.assert_discovery_programs_equal(loaded_program, self.expected_program)
        self.assertEqual(len(responses.calls), 2)

        # this should return the same object from cache
        loaded_program = DiscoveryProgram.get(self.program_uuid)
        self.assert_discovery_programs_equal(loaded_program, self.expected_program)
        self.assertEqual(len(responses.calls), 2)

    @mock_oauth_login
    @responses.activate
    def test_get_discovery_program_error(self):
        """
        Verify if an error occurs when requesting discovery data an exception is
        thown and the cache is not polluted.
        """
        responses.add(
            responses.GET,
            self.discovery_url,
            json={'message': 'everything is broken'},
            status=500
        )

        with self.assertRaises(HTTPError):
            DiscoveryProgram.get(self.program_uuid)

        responses.replace(
            responses.GET,
            self.discovery_url,
            json=self.programs_response,
            status=200
        )
        loaded_program = DiscoveryProgram.get(self.program_uuid)
        self.assert_discovery_programs_equal(loaded_program, self.expected_program)

        nonexistant_program_uuid = str(uuid.uuid4())
        discovery_url = urljoin(
            settings.DISCOVERY_BASE_URL,
            DISCOVERY_PROGRAM_API_TPL.format(nonexistant_program_uuid)
        )
        responses.add(
            responses.GET,
            discovery_url,
            json={'message': 'program not found!'},
            status=404
        )
        with self.assertRaises(Http404):
            DiscoveryProgram.get(nonexistant_program_uuid)

    @mock_oauth_login
    @responses.activate
    def test_get_discovery_cache_versioning(self):
        """
        Verify that bumping the version of the cache invalidates old
        entries.
        """
        responses.add(
            responses.GET,
            self.discovery_url,
            json=self.programs_response,
            status=200
        )
        DiscoveryProgram.get(self.program_uuid)
        self.assertEqual(len(responses.calls), 2)
        bumped_version = DiscoveryProgram.class_version + 1
        with mock.patch.object(DiscoveryProgram, 'class_version', bumped_version):
            DiscoveryProgram.get(self.program_uuid)
        self.assertEqual(len(responses.calls), 4)


@ddt.ddt
class DiscoveryProgramTests(TestCase):
    """ Tests for DiscoveryProgram methods """

    def setUp(self):
        super().setUp()
        program_uuid = str(uuid.uuid4())
        curriculum_uuid = str(uuid.uuid4())
        program_title = "Master's in CS"
        program_url = 'https://stem-institute.edx.org/masters-in-cs'
        program_type = 'Micromasters'
        self.program = DiscoveryProgram(
            version=0,
            loaded=datetime.now(),
            uuid=program_uuid,
            title=program_title,
            url=program_url,
            program_type=program_type,
            active_curriculum_uuid=curriculum_uuid,
            course_runs=[
                self.make_course_run(i) for i in range(4)
            ],
        )

    def make_course_run(self, counter):
        """
        Helper for making DiscoveryCourseRuns
        """
        key = 'course-{}'.format(counter)
        external_key = 'external-key-course-{}'.format(counter)
        title = 'Course {} Title'.format(counter)
        url = 'www.courserun.url/{}/'.format(counter)
        return DiscoveryCourseRun(key, external_key, title, url)

    @ddt.data('key', 'external_key')
    def test_get_key(self, attr):
        for course_run in self.program.course_runs:
            test_key = getattr(course_run, attr)
            self.assertEqual(
                self.program.get_course_key(test_key),
                course_run.key
            )

    def test_get_key_not_found(self):
        for i in [10, 101, 111, 123]:
            not_in_program_run = self.make_course_run(i)
            self.assertIsNone(self.program.get_course_key(not_in_program_run.key))
            self.assertIsNone(self.program.get_course_key(not_in_program_run.external_key))

    @ddt.data('key', 'external_key')
    def test_get_external_key(self, attr):
        for course_run in self.program.course_runs:
            test_key = getattr(course_run, attr)
            self.assertEqual(
                self.program.get_external_course_key(test_key),
                course_run.external_key
            )

    def test_get_external_key_not_found(self):
        for i in [10, 101, 111, 123]:
            not_in_program_run = self.make_course_run(i)
            self.assertIsNone(self.program.get_external_course_key(not_in_program_run.key))
