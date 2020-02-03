API Permissions vs. Internal Permissions
========================================

Context
-------

As features are added to the Program Manager web app
(which uses Registrar as a backend),
it becomes necessary for Program Manager to have a concept of
what the logged-in user can and cannot do,
such that only relevant operations are shown to them.
For example, a user that can only read reports for
Program X should not be shown an enrollment management
interface for Program X.

The permissions we care about in Program Manager
are high-level, generic, and provided within the context of
a specific program.
The following are examples of permissions that a Program Manager
user may be granted.

* See that a program exists.
* Download the enrollments of a program.
* Upload enrollments for a program.
* Download reports for a program.

However, the named permissions that exist in the Registrar database
are more granular.
For instance, for technical reasons, there exist
two possible permissions for each operation listed
previously, the only difference between the two being
*how* the permission was granted.
The four Program Manager operations listed above become the following
in Registrar:

* ``core.organization_read_metadata``
* ``core.program_read_metadata``
* ``core.organization_read_enrollments``
* ``core.program_read_enrollments``
* ``core.organization_write_enrollments``
* ``core.program_write_enrollments``
* ``core.organization_read_reports``
* ``core.program_read_reports``

In the interest of maintaining a consistent REST API
that minimizes complexity exposed to Program Manager and other clients,
we need to establish a distinction between
the business-level permissions used in the API
and the database-level permissions used in Registrar.

Decision
--------

We declare a set of Registrar API Permissions,
each of which may be granted to a user in the context of a program.
Each permission has a short codename.
The initial set, which may grow over time, consists of:

* ``read_metadata``
* ``read_enrollments``
* ``write_enrollments``
* ``read_reports``

Going forward, the list of API Permissions will be maintained in
the Registrar API documentation.
All API endpoints that reference permissions in requests or responses
will use these new permission codenames.

The API permissions that a user of Registrar posseses
are determined by the internal permissions they are assigned within Registrar's database;
however, those internal permissions are not exposed to the user
in the interest of minimizing complexity
and allowing the underlying representation to change if necessary.
The mapping from internal permissions to API permissions
will be defined in ``core/permissions.py``.
Logic to convert from internal to API permissions
will also be defined in that module,
such that conversion logic is not duplicated throughout the codebase.

Example
~~~~~~~

Consider this hypothetical Registrar API interaction,
which aims to read metadata for all programs on which
the user has permission to do so::


  // GET /api/v2/programs/?user_has_perm=read_metdata
  [
    {
      "program_key": "first",
      "permissions": ["read_metadata", "read_enrollments"],
    },
    {
      "program_key": "second",
      "permissions": ["read_metadata", "read_enrollments", "read_reports"],
    },
    {
      "program_key": "third",
      "permissions": ["read_metadata"],
    },
  ]


Without introduction of the API permission layer,
the interaction may have looked like this::

  // GET /api/v2/programs/?user_has_perm=organization_read_metdata
  [
    {
      "program_key": "first",
      "permissions": [
        "core.organization_read_metadata",
        "core.organization_read_enrollments",
      ],
    },
    {
      "program_key": "second",
      "permissions": [
        "core.organization_read_metadata",
        "core.program_read_metadata",
        "core.program_read_enrollments",
        "core.organization_read_reports",
        "core.program_read_reports",
      ]
    },
  ]
  // GET /api/v2/programs/?user_has_perm=program_read_metdata
  [
    {
      "program_key": "second",
      "permissions": [
        "core.organization_read_metadata",
        "core.program_read_metadata",
        "core.program_read_enrollments",
        "core.organization_read_reports",
        "core.program_read_reports",
      ]
    },
    {
      "program_key": "third",
      "permissions": ["core.program_read_metadata"],
    },
  ]

Status
------

Accepted (circa January 2020)


Consequences
------------

1. The groundwork for the internal-to-API permission mapping is being laid in `MST-60`_.
2. The existing endpoint that references permissions (``/api/v2/programs/?user_has_perm=``)
   will be updated in `MST-82`_, preserving backwards compatibility.
3. This change will be implemented in Program Manager in `MST-63`_.

.. _MST-60: https://openedx.atlassian.net/browse/MST-60
.. _MST-63: https://openedx.atlassian.net/browse/MST-63
.. _MST-82: https://openedx.atlassian.net/browse/MST-82
