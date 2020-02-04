"""
The initialization file for the whole registrar project.
Only needed to wire the celery `app` into the project.
"""
from __future__ import absolute_import

from .celery import app as celery_app


__all__ = ("celery_app",)
