Registrar service  |Travis|_ |Codecov|_
===================================================
.. |Travis| image:: https://travis-ci.org/edx/registrar.svg?branch=master
.. _Travis: https://travis-ci.org/edx/registrar

.. |Codecov| image:: http://codecov.io/github/edx/registrar/coverage.svg?branch=master
.. _Codecov: http://codecov.io/github/edx/registrar?branch=master

The Registrar service allows external organizations to integrate with edX programs,
providing REST APIs involving program structure, enrollment, and grading.

Through Django Admin, it allows the definition of access roles for different API users.

It supports import and exporting of enrollment data through `Program Manager <https://github.com/edx/frontend-app-program-manager>`_.

 
Using with Devstack
-----------------

The best way to run Registrar is within the edX Devstack: https://github.com/edx/devstack.

See the Devstack README for information on how to install and run Registrar.

Using Standalone
-----------------

Alternatively, you may run Registrar locally without the edX Devstack. Note that in this configuration, functionality that depends on communication with other edX services (e.g. LMS authentication) will not work by default.

Requirements:

- Python 3

- python3-pip

- virtualenv (`pip3 install virtualenv`)

- python3.X-dev, where X is the minor version of your Python 3 installation

- Optional, for ``dbshell-local``: sqlite3

First, clone this respository with one of the following::

  git clone https://github.com/edx/registrar
  git clone git@github.com:edx/registrar.git

Navigate in, create a Python 3 virtualenv, and activate it::

  cd registrar
  virtualenv --python=python3 venv
  source venv/bin/activate

Ensure local settings are used instead of Devstack settings::

  export DJANGO_SETTINGS_MODULE=registrar.settings.local

This above command must be run every time you open a new shell
to run Registrar in. Alternatively, you can append it to the end of
``venv/bin/activate`` so that it is run upon activation of your virtualenv.
If you do so, you may want to add ``unset DJANGO_SETTINGS_MODULE``
to the ``deactivate()`` function of the same file.


Next, install requirements, run migrations, and create the default superuser::

  make local-requirements
  make migrate
  make createsuperuser

Run the server::

  make run-local

Finally, navigate to https://localhost:8000.


API Documentation
-----------------

Endpoints of this api can be tested using the swagger page served on the ``/api-docs`` path.  This UI is driven by an openapi specification in `api.yaml <./api.yaml>`_.
A second version of this document, `.api-generated.yaml <./.api-generated.yaml>`_, can be generated to expose the spec to external tools that are unable to parse yaml anchors.  All manual edits should be made to `api.yaml <./api.yaml>`_.  The generated file should only be updated using the process outlined below.

To add/update endpoints or parameters:
  1. make your changes to api.yaml
  2. restart the registrar application and validate appearance on the ``/api-docs`` page
  3. before merging your changes run ``make api_generated``. This will create the expanded document.
  4. commit new  `.api-generated.yaml <./.api-generated.yaml>`_ file


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


License
-------

The code in this repository is licensed under version 3 of the AGPL unless otherwise noted. Please see the LICENSE_ file for details.

.. _LICENSE: https://github.com/edx/registrar/blob/master/LICENSE
