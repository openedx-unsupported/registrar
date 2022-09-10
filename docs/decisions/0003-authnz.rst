Authentication and Authorization
================================

Context
-------

External API clients of the Registrar service will need to be authenticated (AuthN) and authorized (AuthZ)
to access the resources they request.  An API client will usually correspond to a human associated
with a Master's partner institution (school) who will make HTTP requests of registrar.  The purpose
of these requests is to either read data about resources, create resources, or update resources.

Decision
--------

Authentication
~~~~~~~~~~~~~~

1. We'll use the LMS as the identity provider for registrar.  It will provide a JSON Web Token (JWT)
   to authenticated users.
2. The ``edx-drf-extensions`` library provides an authentication class ``JwtAuthentication``
   which will facilitate the creation of a ``core_user`` account in registrar based on the user profile
   information provided in the JWT.
3. The LMS endpoint ``/api-admin/`` will allow API clients of registrar to manage their own OAuth2 client credentials.
   See https://github.com/openedx/edx-platform/tree/master/openedx/core/djangoapps/api_admin
4. We'll also allow authenticated clients to access the DRF browsable API.

Authorization
~~~~~~~~~~~~~

1. We'll implement a lightweight version of role-based access control (RBAC) of registrar API resources.
2. Every API client associated with a school will be a member of one or more "Access Control" groups.  These
   groups are extended Django groups that we can associate an ``Organization`` with.
3. Each group will be granted a set of permissions on an ``Organization`` entity associated with their
   school.
4. Any group that has a permission on a given ``Organization`` object will be assumed to have that same
   permission on any resource that falls under that organization (e.g. ``Programs``, ``Courses``, and ``Enrollments``).
5. We'll use the ``django-guardian`` library to assign and check object-level permissions on ``Organizations``.
6. Internal staff-level permissions will be granted to vanilla Django groups.  These groups will be granted
   permissions "globally", i.e. they will not be associated with any particular ``Organization``.  ``django-guardian``
   provides adequate permission-checking tools for this strategy.

Status
------

Accepted (circa March 2019)

Consequences
------------

1. In the context of global permission-checking and Guardian's ``PermissionRequiredMixin`` for view-set classes,
   it's going to be easier if we break out retrieval actions and list actions
   (i.e. get one program vs. get many programs) into separate view sets - the logic for fetching an
   ``Organization`` object in the context of a retrieval action (where we're passed a program key) vs.
   fetching an ``Organization`` object during a list action (where we're passed either an org key or nothing at all)
   is sufficiently different to warrant this.
2. We know of at least one school with two programs - call them "A" and "B" - where administrators of program
   A should not be able to access resources from program B, and vica versa.  We have two options here:

   a. Create distinct ``Organizations`` for "A" and "B".  The downside here is that we lose the ability to
      do roll-up types of reports.
   b. Assign permissions at the program level in some cases, and modify our permission-checking scheme
      to deal with that scenario. See 0004-program-authz_ for implementation of program level permissions.

Resources
---------

1. https://openedx.atlassian.net/wiki/spaces/MS/pages/952009187/Registrar+AuthN+Z+Discovery
2. https://openedx.atlassian.net/browse/EDUCATOR-4154 (Internal staff permissions discovery)

.. _0004-program-authz: https://github.com/openedx/registrar/blob/zhancock/reporting-decision/docs/decisions/0004-program-authz.rst
