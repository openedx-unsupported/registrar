""" Constants for the core app. """


class Status(object):
    """Health statuses."""
    OK = u"OK"
    UNAVAILABLE = u"UNAVAILABLE"


# Pulled from edx-platform. Will correctly capture both old- and new-style
# course ID strings.
COURSE_ID_PATTERN = r'(?P<course_id>[^/+]+(/|\+)[^/+]+(/|\+)[^/?]+)'

# Captures strings composed of alphanumeric characters, dashes, and underscores.
PROGRAM_KEY_PATTERN = r'(?P<program_key>[A-Za-z0-9-_]+)'
