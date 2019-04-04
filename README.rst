Registrar service  |Travis|_ |Codecov|_
===================================================
.. |Travis| image:: https://travis-ci.org/edx/registrar.svg?branch=master
.. _Travis: https://travis-ci.org/edx/registrar

.. |Codecov| image:: http://codecov.io/github/edx/registrar/coverage.svg?branch=master
.. _Codecov: http://codecov.io/github/edx/registrar?branch=master

The registrar service links an edX learner user with an edX program stored in course discovery.
 
Using with Devstack
-----------------

The best way to run Registrar is within the edX Devstack: https://github.com/edx/devstack.

After setting up Devstack, clone the Registrar repository::

  make registrar-clone
 
Bring up Registrar, along with the other Devstack containers::

  make up-registrar-detached

Install requirements, do migrations, create a superuser, and create an IDA user::

  make registrar-setup

To bring all containers down::
 
  make down-registrar

To view all commmands::

  make help-registrar

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


How Authentication Works
------------------------

Authentication from the Registrar service against LMS or Discovery
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following steps will help your local Registrar container communicate with your local
Discovery and LMS services.

#. Create a ``registrar_worker`` user on LMS.

#. Setup a Django Oauth Toolkit (DOT) application for ``registrar_worker`` in your local LMS.
   See examples at http://localhost:18000/admin/oauth2_provider/application/

#. When making API calls into LMS or Discovery service within Registrar,
   leverage the edx-rest-api-client library https://github.com/edx/edx-rest-api-client/blob/master/edx_rest_api_client/client.py#L88
   by providing `settings.BACKEND_SERVICE_EDX_OAUTH2_KEY` and `settings.BACKEND_SERVICE_EDX_OAUTH2_SECRET`.


Authentication from External system against Registrar API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Configure the registrar service with the proper value for JWT token authentication. This should be automatically done using the configuration playbook at https://github.com/edx/configuration/blob/master/playbooks/roles/edx_django_service/defaults/main.yml#L158

#. Create a new worker user for the school's system on LMS

#. Using the worker user above, setup a Django Oauth Toolkit (DOT) application on LMS. This is done at http://localhost:18000/admin/oauth2_provider/application/

#. Send the school their client_key and client_secret created from the step above

#. The school's system need to use the client_key and client_secret above to get auth token from LMS, then use the auth token for API calls against registrar service


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
