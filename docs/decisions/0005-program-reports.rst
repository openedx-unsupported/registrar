Program Report Access
=====================

Context
-------
We currently have a system for generating CSV reports on enrollment numbers and the general health of program. These reports are stored in an s3 bucket with limited access. This project will add a self-service method for external partners to access those files through the Program Manager UI. Additionally, we want to provide the mechanisms for partners to configure that access to specific users either on a program by program basis or at the more generic organization level. We believe expanding the Registrar service to handle serving these reports to the UI application is the best path forward.

As it stands today, Registrar is limited to the management of enrollments for master's programs. We wish to widen this context and act as an interface for programs of all types. Much of business logic required to setup and interact with a program already exists in this service. A second driving factor in this decision is the existing role-based access control in Registrar which allows us to grant users permissions at specific entities. This existing system can easily be modified to fit our needs for managing access to program reports (see 0004-program-authz_). By expanding the scope of Registrar we can keep program management code in one place as well as be the one stop shop for configuring role based access to program data.

Decision
--------
1. Registrar, and by extension the Program Manager frontend, will act as the access mechanism for retrieving program report files.

2. A new reporting app will be added to the service that will expose endpoints to list and retrieve available reports.

3. We will add a ``type`` field to the ``Program`` model so MicroMasters and Professional Certificate programs may be configured in the service at the request of the partner.

4. Endpoints for creating or retrieving enrollments will now require the requested program be of type `Masters` in addition to checking a user's permissions.

5. A new role will be added to grant access to program reports. Existing roles will be refactored to be specific to either enrollment or reporting allowing us to configure access to those features separately.



Status
------
Accepted (circa December 2019)

.. _0004-program-authz: https://github.com/openedx/registrar/edit/zhancock/reporting-decision/docs/decisions/0004-program-authz.rst

Resources
---------
https://openedx.atlassian.net/wiki/spaces/MS/pages/1051230962/Analytics+Program+Analytics
