"""
Test for common data functions
"""

from posixpath import join as urljoin
from uuid import UUID

import ddt
import responses
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase

from ..data import DISCOVERY_PROGRAM_API_TPL, DiscoveryProgram
from .factories import DiscoveryProgramFactory
from .utils import mock_oauth_login, patch_discovery_data


def make_course_run(n, with_external_key=False):
    """
    Return a course run dictionary for testing.

    If `with_external_key` is set to True, set ext key to testorg-course-${n}.
    """
    return {
        'key': 'course-v1:TestRun+{}'.format(n),
        'external_key': (
            'testorg-course-{}'.format(n)
            if with_external_key
            else None
        ),
        'title': 'Test Course {}'.format(n),
        'marketing_url': 'https://stem.edx.org/masters-in-cs/test-course-{}'.format(n),
        'extraneous_data': ['blah blah blah'],
    }


@ddt.ddt
class DiscoveryProgramTestCase(TestCase):
    """
    Test DiscoveryProgram proxy model.
    """
    program_uuid = UUID("88888888-4444-2222-1111-000000000000")
    discovery_url = urljoin(
        settings.DISCOVERY_BASE_URL,
        DISCOVERY_PROGRAM_API_TPL.format(program_uuid)
    )

    inactive_curriculum_uuid = UUID("77777777-4444-2222-1111-000000000000")
    active_curriculum_uuid = UUID("77777777-4444-2222-1111-000000000001")
    ignored_active_curriculum_uuid = UUID("77777777-4444-2222-1111-000000000002")

    make_course_run = make_course_run

    program_data = {
        'title': "Master's in CS",
        'marketing_url': "https://stem.edx.org/masters-in-cs",
        'type': "Masters",
        'curricula': [
            {
                # Inactive curriculum. Should be ignored.
                'uuid': str(inactive_curriculum_uuid),
                'is_active': False,
                'courses': [{'course_runs': [make_course_run(0, True)]}],
            },
            {
                # Active curriculum. All three course runs should be aggregated.
                'uuid': str(active_curriculum_uuid),
                'is_active': True,
                'courses': [
                    {'course_runs': [make_course_run(1)]},
                    {'course_runs': []},
                    {'course_runs': [make_course_run(2, True), make_course_run(3)]},
                    {'course_runs': [{'this course run': 'has the wrong format'}]},
                ]
            },
            {
                # Second active curriculum.
                # In current implementation, should be ignored.
                'uuid': str(ignored_active_curriculum_uuid),
                'is_active': True,
                'courses': [{'course_runs': [make_course_run(4, True)]}],
            },
        ],
    }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        DiscoveryProgramFactory(key="masters-in-cs", discovery_uuid=cls.program_uuid)

    def setUp(self):
        super().setUp()
        cache.clear()

    @classmethod
    def get_program(cls):
        """
        Loads the program with `cls.program_uuid`
        """
        return DiscoveryProgram.objects.get(discovery_uuid=cls.program_uuid)

    @mock_oauth_login
    @responses.activate
    @ddt.data(
        (200, program_data, program_data),
        (200, {}, {}),
        (200, 'this is a string, but it should be a dict', {}),
        (404, {'message': 'program not found'}, {}),
        (500, {'message': 'everything is broken'}, {}),
    )
    @ddt.unpack
    def test_discovery_program_get(self, disco_status, disco_data, expected_data):
        responses.add(
            responses.GET,
            self.discovery_url,
            status=disco_status,
            json=disco_data,
        )
        loaded_program = self.get_program()
        assert isinstance(loaded_program, DiscoveryProgram)
        assert loaded_program.discovery_uuid == self.program_uuid
        assert loaded_program.discovery_data == expected_data
        self.assertEqual(len(responses.calls), 2)

        # This should used the cached Discovery response.
        reloaded_program = self.get_program()
        assert isinstance(reloaded_program, DiscoveryProgram)
        assert reloaded_program.discovery_uuid == self.program_uuid
        assert reloaded_program.discovery_data == expected_data
        self.assertEqual(len(responses.calls), 2)

    @patch_discovery_data(program_data)
    def test_active_curriculum(self):
        program = self.get_program()
        assert program.active_curriculum_uuid == self.active_curriculum_uuid
        assert len(program.course_runs) == 4
        assert program.course_runs[0].title == "Test Course 1"
        assert program.course_runs[-1].title is None

    @patch_discovery_data({})
    def test_no_active_curriculum(self):
        program = self.get_program()
        assert program.active_curriculum_uuid is None
        assert not program.course_runs

    @patch_discovery_data(program_data)
    @ddt.data(
        # Non-existent course run.
        ('non-existent', None, None),
        # Real course run, but not in active curriculum.
        ('course-v1:TestRun+0', None, None),
        ('testorg-course-0', None, None),
        # Real course run, in active curriculum, only has internal course key.
        ('course-v1:TestRun+1', 'course-v1:TestRun+1', None),
        ('testorg-course-1', None, None),
        # Real course run, in active curriculum, has internal and external keys.
        ('course-v1:TestRun+2', 'course-v1:TestRun+2', 'testorg-course-2'),
        ('testorg-course-2', 'course-v1:TestRun+2', 'testorg-course-2'),
    )
    @ddt.unpack
    def test_get_course_keys(self, argument, expected_course_key, expected_external_key):
        program = self.get_program()
        actual_course_key = program.get_course_key(argument)
        assert actual_course_key == expected_course_key
        actual_external_key = program.get_external_course_key(argument)
        assert actual_external_key == expected_external_key
