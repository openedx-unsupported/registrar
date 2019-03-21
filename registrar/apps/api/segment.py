"""
Convenience functions for working with the segment.io analytics library
"""
import logging
import analytics
from django.conf import settings

logger = logging.getLogger(__name__)


def track(
    user_id,
    event,
    properties=None,
    context=None,
    timestamp=None,
    anonymous_id=None,
    integrations=None,
):
    if settings.SEGMENT_KEY:
        analytics.track(user_id, event, properties, context, timestamp, anonymous_id, integrations)
    else:
        logger.debug("{{{}, {}}} not tracked because SEGMENT_KEY not set".format(user_id, event))
