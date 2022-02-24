Storing Program Enrollment within edX Platform
==============================================

Context
-------

Currently, the idea of "program enrollments" does not exist explictly anywhere
in the edX ecosystem.
The relationship is implicitly deductible, as
it can be assumed that when a learner is enrolled in the verified track
of a program's course, that they are enrolled in said program.
However, there is no table anywhere that links together students and programs,
like there is for students and courses. For Master's degree programs, this implicit
enrollment system will not suffice.
While it is clear that a ProgramEnrollment table must created, there has been
debate over exactly where that table belongs.

One view is that the table belongs in the Registrar service.
This prevents us from introducing additional features into edX Platform,
which is generally considered to be overly large and complex.
Additionally, as Registrar is currently planned to only service Master's programs,
it would allow for us to tailor the table to Master's business needs,
instead of taking into consideration all edX Programs.

The opposing view is that the table belongs within the LMS application of the edX Platform.
Program enrollments should be considered a core edX concept,
and are likely to be needed by other edX services and frontends
(e.g., the Master's Student Dashboard).
It would be undesirable for other parts of the edX ecosystem to depend on a Registrar,
an integration point, for authoritative data.
Furthermore, if program enrollments were stored in Registrar,
then "preemptive program enrollments"
(program enrollments made for a students who do not yet have edX accounts)
would also need to be stored in Registrar.
This would require the LMS to somehow communicate to Registrar whenever a learner
account is created, so that any corresponding preemptive enrollments can be activated.
It would be simpler to implement program enrollments, both preemptive and actual,
within the LMS.

Finally, an alternative viewpoint was for creating an "Enrollments Service" to store
both preemptive and actual program enrollments (and, in the future, course enrollments),
while having the Registar remain solely an integration point.
This would both avoid adding features to the LMS as well as avoid adding authoritative
core data to Registrar.
However, there was worry that migrating course enrollments over to such an Enrollments
Service would be a time-consuming task that may not be tackled for a long time,
leaving the service as a "half-baked" system that would actually increase
complexity over time instead of decreasing it.

Decision
--------

We have decided that storing program enrollments
(along with preemptive course and program enrollments)
within edX Platform is the best solution,
in terms of both architectural integrity and ease of implementation.

Status
------

Accepted (circa March 2019)

Consequences
------------

* The ``ProgramEnrollment`` and ``Learner`` models in Registrar will no longer be authoritative data sources. We may or may not store program enrollments in Registrar non-authoritatively for caching and/or validation purposes.
* The ``ProgramEnrollment`` models will be created within LMS.
* Preemptive program and course enrollments will be stored within the LMS, either through an existing mechanism or by the creation of new ``PreemptiveProgramEnrollment`` and ``PreemptiveCourseEnrollment`` tables.
* Program enrollment will be added to the current LMS Enrollment API.
* A preemptive enrollment API will be created within the LMS.

Notes
-----

For a deeper delve into the process that lead to this decision, see: https://openedx.atlassian.net/wiki/spaces/AC/pages/3345121583/Master+s+Enrollment+Integration+Architectural+Review
