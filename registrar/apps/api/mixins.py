"""
Mixins common to more than one version of the REST API.
"""
import json
import logging

from registrar.apps.core.permissions import APIPermission

from . import segment


logger = logging.getLogger(__name__)


class TrackViewMixin:
    """
    A mixin to provide tracking utility for all the views

    The mixin operates by overriding the `dispatch` method and uses the
    `request` attribute, so it should only be used on Django views.

    The names of the events must be set by overriding `event_method_map`,
    which maps HTTP methods (capitalized) to event names.
    The names of properties containing the values of URL path/query parameters
    can be set by overriding `event_parameter_map`.
    Furthermore, events contain a list organizations to which the user belongs.
    Finally, additional data can be added by calling `add_tracking_data`.

    The tracking sends events to both Segment and logging files.
    """

    # Map from an HTTP method to the name of the event for that method.
    # Override in subclass.
    # Example:
    #   event_method_map = {
    #       'GET': 'registrar.vN.get_item',
    #       'POST': 'registrar.vN.create_item'
    #   }
    event_method_map = {}

    # Map from a URL query/path parameter name to the name of the event
    # property that will have its value.
    # Example:
    #   event_parameter_map = {
    #       'org': 'organization_filter',
    #       'fmt': 'file_format'
    #   }
    event_parameter_map = {}

    def __init__(self, *args, **kwargs):
        """
        Initialize tracking data.
        """
        super().__init__(*args, **kwargs)
        self._extra_tracking_data = {}

    def add_tracking_data(self, **kwargs):
        """
        Add fields to the tracking event.
        """
        cleaned_data = self._ensure_missing_permissions_are_valid_json(kwargs)
        self._extra_tracking_data.update(cleaned_data)

    @staticmethod
    def _ensure_missing_permissions_are_valid_json(data):
        """
        Given some tracking data, return a copy of the tracking data where the values in
        the missing_permissions field (if any) can be rendered as JSON.

        Arguments:
            data (dict)

        Returns: dict
        """
        cleaned_data = data.copy()
        missing_perms = cleaned_data.get('missing_permissions')
        if missing_perms:
            cleaned_data['missing_permissions'] = [
                (perm.name if isinstance(perm, APIPermission) else perm)
                for perm in missing_perms
            ]
        return cleaned_data

    def dispatch(self, *args, **kwargs):
        """
        Intercept dispatch method, which handles all requests, in order to
        fire tracking event.
        """
        response = super().dispatch(*args, **kwargs)
        if self.request.user.is_authenticated:
            self._track(response.status_code)
        return response

    def _track(self, status_code):
        """
        Send the tracking event to Segment and the logs.

        Properties included in the tracking event includes:
        * Default data from `get_tracking_properties`
        * URL query & path parameters, named by `event_parameter_map`
        * Everything in `self._extra_tracking_data` dictionary
        * HTTP response status code
        """
        event_name = self.event_method_map.get(self.request.method)
        api_version = self.request.get_full_path().split('/')[2]
        if not event_name:  # pragma: no cover
            logger.error(
                'Segment tracking event name not found for request method %s on view %s',
                self.request.method,
                self.__class__.__name__,
            )
            return

        event_name = event_name.format(api_version=api_version)
        params = list(self.kwargs.items()) + list(self.request.GET.items())
        param_properties = {
            self.event_parameter_map[key]: value
            for key, value in params
            if key in self.event_parameter_map
        }

        properties = segment.get_tracking_properties(self.request.user)
        properties.update(param_properties)
        properties.update(self._extra_tracking_data)
        properties['status_code'] = status_code

        context = {
            'page': {
                'path': self.request.path,
                'referrer': self.request.headers.get('referer'),
                'url': self.request.build_absolute_uri(),
            },
            'userAgent': self.request.headers.get('user-agent'),
        }

        segment.track(self.request.user.username, event_name, properties, context)
        logger.info(
            '%s invoked on Registrar by user with ID=%s with properties %s and context %s',
            event_name,
            self.request.user.id,
            json.dumps(properties, skipkeys=True, sort_keys=True),
            json.dumps(context, skipkeys=True, sort_keys=True)
        )
