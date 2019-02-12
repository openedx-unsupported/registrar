Registrar service  |Travis|_ |Codecov|_
===================================================
.. |Travis| image:: https://travis-ci.org/edx/registrar.svg?branch=master
.. _Travis: https://travis-ci.org/edx/registrar

.. |Codecov| image:: http://codecov.io/github/edx/registrar/coverage.svg?branch=master
.. _Codecov: http://codecov.io/github/edx/registrar?branch=master

The registrar service links an edX learner user with an edX program stored in course discovery.

Using Locally
-------------

This can be run locally with docker.  It uses the ``devstack_default`` network.

First, you have to build the images::

  make build

Secondly, bring up the application container, memcache container, and DB container::

  make up

Lastly, you'll need to provision data to your mysql contianer::

  make provision

To bring these containers down::

  make down

The way we're providing container configuration is via docker environment files.
The ``registrar-app.env.template`` defines a template for including environment variables
in your running registrar container.  Replace the dummy values in that file with
real values to configure rest clients for communication with other services, etc.

If you wish to bring the containers down and destroy your database volumes, run::

  make destroy


How Authentication Works
------------------------

Authentication from the Registrar service against LMS or Discovery
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following steps will help your local Registrar container communicate with your local
Discovery and LMS services.

#. Create a ``registrar_worker`` user on LMS.

#. Setup a Django Oauth Toolkit (DOT) application for ``registrar_worker`` in your local LMS.
   See examples at http://localhost:18000/admin/oauth2_provider/application/

#. Store the ``client_key`` and ``client_secret`` created from step above in your ``registrar-app.env`` file.

#. When making API calls into LMS or Discovery service within Registrar,
   leverage the edx-rest-api-client library https://github.com/edx/edx-rest-api-client/blob/master/edx_rest_api_client/client.py#L88
   by providing the client_key and client_secret above.


Authentication from External system against Registrar API
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

#. Configure the registrar service with the proper value for JWT token authentication. This should be automatically done using the configuration playbook at https://github.com/edx/configuration/blob/master/playbooks/roles/edx_django_service/defaults/main.yml#L158

#. Create a new worker user for the school's system on LMS

#. Using the worker user above, setup a Django Oauth Toolkit (DOT) application on LMS. This is done at http://localhost:18000/admin/oauth2_provider/application/

#. Send the school their client_key and client_secret created from the step above

#. The school's system need to use the client_key and client_secret above to get auth token from LMS, then use the auth token for API calls against registrar service

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
