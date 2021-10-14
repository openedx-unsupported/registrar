""" Tests for segment.py """

from unittest import mock

from django.conf import settings
from django.test import TestCase

from registrar.apps.api import segment


class SegmentTrackTests(TestCase):
    """ Test segment.track """

    EVENT_DATA = {'key': 'value'}

    @mock.patch.object(settings, 'SEGMENT_KEY', new='dummy-value')
    @mock.patch('registrar.apps.api.segment.analytics.track', autospec=True)
    def test_track(self, mock_inner_track):
        segment.track(user_id=1, event=self.EVENT_DATA)
        mock_inner_track.assert_called_once_with(
            1, self.EVENT_DATA, None, None, None, None, None
        )

    @mock.patch.object(settings, 'SEGMENT_KEY', new=None)
    def test_track_no_segment_key(self):
        with self.assertLogs(level='DEBUG') as log:
            segment.track(user_id=1, event=self.EVENT_DATA)
        self.assertEqual(
            log.records[0].getMessage(),
            r"{1, {'key': 'value'}} not tracked because SEGMENT_KEY not set"
        )
