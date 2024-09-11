⚠️ DEPRECATION WARNING
======================

This repository is `deprecated`_. It will no longer receive maintenance, support, or updates from the Open edX project.

At the time of writing, edX.org still runs `a fork`_ of this repository, but neither they nor the Open edX project make any guarantees about the stability or long-term availability of that code.

.. _deprecated: https://github.com/openedx/public-engineering/issues/276
.. _a fork: https://github.com/edx/registrar

Registrar service  |Travis|_ |Codecov|_
===================================================

.. |Codecov| image:: http://codecov.io/github/openedx/registrar/coverage.svg?branch=master
.. _Codecov: http://codecov.io/github/openedx/registrar?branch=master

The Registrar service allows external organizations to integrate with Open edX programs,
providing REST APIs involving program structure, enrollment, and grading.

Through Django Admin, it allows the definition of access roles for different API users.

It supports import and exporting of enrollment data through `Program Console`_.

.. _Program Manager: https://github.com/openedx/frontend-app-program-console


Coding Guidelines
-----------------

Before opening a PR, please check out the `Registrar Coding Guide`_,
which contains code style conventions
as well as important information about PII annotation.

.. _Registrar Coding Guide: docs/coding-guide.rst

Using with Devstack
-----------------

! Note ! This section may be outdated. Tutor (https://docs.tutor.edly.io/gettingstarted.html) is now the supported development environment for the Open edX project, but we have not currently verified if Registrar works on Tutor.

The best way to run Registrar is within the edX Devstack: https://github.com/openedx/devstack.

See the Devstack README for information on how to install and run Registrar.

Using Standalone
-----------------

Alternatively, you may run Registrar locally. Note that in this configuration, functionality that depends on communication with other Open edX services (e.g. LMS authentication) will not work by default.

Requirements:

- Python 3

- python3-pip

- virtualenv (`pip3 install virtualenv`)

- python3.X-dev, where X is the minor version of your Python 3 installation

- Optional, for ``dbshell-local``: sqlite3

First, clone this respository with one of the following::

  git clone https://github.com/openedx/registrar
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

Endpoints of this api can be tested using the swagger page served on the ``/api-docs`` path.  This UI is driven by edX api-doc-tools, which makes use of openapi.

To add/update endpoints or parameters:
  1. make your changes to the @schema decorators associated with each endpoint
  2. restart the registrar application and validate appearance on the ``/api-docs`` page

License
-------

The code in this repository is licensed under version 3 of the AGPL unless otherwise noted. Please see the LICENSE_ file for details.

.. _LICENSE: https://github.com/openedx/registrar/blob/master/LICENSE
