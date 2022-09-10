Program Level Authorization
===========================

Context
-------

As the scope of programs in the Registrar service expands we run into multiple cases where granting a user access to all programs within an organization is not desirable. An organization composed of two programs, "A" and "B", may wish to assign certain administrators access to only "A" or only "B", but not the other. To solve this, we will expand our permission model to allow permissions to be assigned to a specific program.

This model also aims to handle the eventual support for programs with multiple authoring organizations. For example, in the case of program reports, the resulting content may differ between users acting on behalf of one organization or another. Permissions granted the program level must still have some `Organization` context to allow for this.

Decision
--------
1. We will expand on the existing role-based access control model outlined in 0003-authnz_ to add a new type of access control group called ``ProgramOrgGroup``.

2. A ``ProgramOrgGroup`` will be associated with a single Program. Providing access to that ``Program`` resource and any resource that falls under it. (e.g. ``Courses`` and ``Enrollments``)

3. A ``ProgramOrgGroup`` will also be associated with an ``Organization``. This does not provide access but acts as a reference to the ``Organization`` granting the role. This ``Organization`` value must be one the program's managing organizations.

4. A user's permissions at a requested object will be defined as the union of all permissions granted on that object and all parents of that object.  In the case of a ``Program`` request, we must look at both the ``Program`` and each of its managing organizations to determine permissions.


Status
-------
Accepted (circa December 2019)

.. _0003-authnz: https://github.com/openedx/registrar/blob/master/docs/decisions/0003-authnz.rst
