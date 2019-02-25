"""
Utilities related to API permissions.
"""

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from registrar.apps.enrollments.models import Program


class program_access_required(object):
    """
    Ensure the user making the API call has the specified access level to the program.

    Expected parameters of wrapped function:
    * self (View)
    * request (Request)
    * program (Program)

    Note that the function would take a program *key* if it were not wrapped.
    Because we must load the `Program` from the database when doing the
    access check, we pass the `Program` object in to the wrapped function
    instead of just passing the key in, saving us an SQL query.

    Usage::
        @program_access_required(ACCESS_WRITE)
        def my_view(self, request, program):
            # Some functionality ...
    """

    def __init__(self, access_level):
        self._access_level = access_level
        self._view_fn = None

    def __call__(self, view_fn):
        self._view_fn = view_fn

        def _wrapper(view, request, program_key):
            program = get_object_or_404(Program.objects.all(), key=program_key)
            if program.check_access(request.user, self._access_level):
                return self._view_fn(view, request, program)
            else:
                return HttpResponseForbidden()

        return _wrapper
