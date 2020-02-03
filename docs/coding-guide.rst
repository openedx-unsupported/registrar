Registrar Coding Guidelines
===========================

Following the guidelines below will help us maintain
a consistent and more-easily maintainable codebase.


Annotating and Checking PII
---------------------------

As part of edX's GDPR compliance, every Django model requires either positive (when the model
stores PII) or negative (no PII is stored) annotations.  For example::

  class MyModel(models.Model):
    """
    Normal description for this model.
    .. pii:: the field named pii_field contains pii...
    .. pii_types:: <comma separated list of the types of PII stored here, required if the PII annotation exists>
    .. pii_retirement:: local_api
    """
    pii_field = models.CharField(max_length=255)

And in the negative case::

  class MyModel(models.Model):
    """
    Normal description for this model.
    .. no_pii::
    """

We must also capture annotations for models generated via 3rd-party libraries.
We use the ``.annotations_safe_list.yml`` file to capture such annotations, with entries as follows::

  sessions.Session:
    ".. no_pii::": "This model has no PII"
  enrollments.HistoricalLearner:
    ".. pii::": "Learner email_address."
    ".. pii_types::": email_address
    ".. pii_retirement::": local_api

You can check that all models are annotated by running the ``make pii_check`` command
from inside a registrar container/shell.


General Coding Style
--------------------

Please follow the `edX Python Style Guide`_,
as well as `PEP-8`_,
with the former taking precedence over the latter.

.. _edX Python Style Guide: https://edx.readthedocs.io/projects/edx-developer-guide/en/latest/style_guides/python-guidelines.html
.. _PEP-8: https://www.python.org/dev/peps/pep-0008/


Imports
-------

Order
~~~~~

Imports are sorted automatically using `isort`_ with a `configuration`_
compatible with the `Black`_ code formatter, even though this
repository does not (yet) use Black.

.. _isort: https://github.com/timothycrosley/isort
.. _configuration: ../setup.cfg
.. _Black: https://github.com/psf/black

Absolute vs. Relative
~~~~~~~~~~~~~~~~~~~~~

Use a **relative import** when importing from a module in the
same directory or in the parent directory::

  from .mixins import AppSpecificMixin

Use an **absolute import** otherwise::

  import registrar.apps.core.mixins import CoreMixin

Why? Consider the following block of imports
from `registrar.apps.enrollments.data <../registrar/apps/enrollments/data.py>`_::

  import json
  import logging
  from itertools import groupby
  from posixpath import join as urljoin

  from django.conf import settings
  from rest_framework.status import (
      HTTP_200_OK,
      HTTP_201_CREATED,
      HTTP_207_MULTI_STATUS,
      HTTP_422_UNPROCESSABLE_ENTITY,
  )

  from registrar.apps.core.data import (
      DiscoveryProgram,
      _do_batched_lms_write,
      _get_all_paginated_results,
  )

  from .constants import (
      ENROLLMENT_ERROR_DUPLICATED,
      ENROLLMENT_ERROR_INTERNAL,
      LMS_ENROLLMENT_WRITE_MAX_SIZE,
  )
  from .serializers import CourseEnrollmentSerializer, ProgramEnrollmentSerializer


The are a few benefits with the same-directory imports being relative here.
They are less verbose,
and it would be easier to rename the enclosing directory if necessary.
More significantly, though,
having ``.constants`` and ``.serializers`` be relative imports
makes it clearer that they are imports from within the same Django app (``enrollments``),
as opposed to another Django app like ``core``.
Keeping this distinction is helpful in maintaining an acyclical app dependency structure

Acyclical App Dependency Structure
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Strive to keep it so that inter-app dependencies
(essentially: which Django apps rely on which, based on the
import statements in their modules)
do not form a circuluar structure.

To put that in context for Registrar,
here are four Registrar apps,
with arrows pointing in the direction of the dependency
(so, `api ---> grades` means "api depends upon grades")::


      +-------api-------+
      |        |        |
      |        |        |
      v        |        v
    grades     |   enrollments
      |        |        |
      |        |        |
      |        v        |
      +----> core <-----+


This is a good structure,
in that if you start at one app and follow arrows,
you cannot end up back at the same app.
In other words, it is "acyclical".
Contrast this to the next scenario,
where some module in ``core`` imports a module from ``api``,
thus creating a cyclical dependency structure::


      +-------api-------+
      |        ^        |
      |        |        |
      v        |        v
    grades     |   enrollments
      |        |        |
      |        |        |
      |        v        |
      +----> core <-----+


Why is the second scenario worse?
In short, it makes it harder to refactor parts of Registrar.
Imagine that we wanted to refactor ``api``.
In the acyclical scenario, this may require little to no change to any of the other apps.
In the cyclical scenario, though, it will likely require changes to ``core``,
which may require changes to both ``grades`` and ``enrollments``,
which may in turn require more changes to ``api``.
