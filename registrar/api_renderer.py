"""
Renders a yaml API spec to an HTML/JavaScript view
"""
import copy
import json
import os

import yaml
from django.conf import settings
from django.shortcuts import render

module_dir = os.path.dirname(__file__)
spec_file = open(os.path.join(module_dir, "../api.yaml"))
API_SPEC = yaml.safe_load(spec_file.read())


def render_yaml_spec(request):
    """
    Render swagger ui using the api yaml spec
    """
    spec = copy.deepcopy(API_SPEC)
    if not request.user.is_authenticated:  # pragma: no branch
        spec["paths"] = {}

    return render(
        request,
        template_name="swagger.html",
        context={
            "request": request,
            "spec": json.dumps(spec),
            "LOGOUT_URL": settings.LOGOUT_URL,
            "LOGIN_URL": settings.LOGIN_URL,
        },
    )
