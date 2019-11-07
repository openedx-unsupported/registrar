Why we need a Registrar service
===============================

Context
=======

The viability of Master’s programs on edX will be partly determined by the extent to which schools
can scale admissions beyond what they can currently handle on campus.  This needs to be supported by edX
reducing operational friction to a minimum, both at the schools and at edX.
In order to affect this we need to automate as many operational procedures as possible,
and eliminate wherever possible the need for any manual procedures by either school or edX staff.
Different schools may manage their program enrollees differently,
but we want to provide a common interface for the management of program enrollees on edX.
This will ensure that we can provide a consistent experience for all Master's students
and provide a common set of data and integration points to all of our partners.
The following points of integration have been identified:

#. Program admission
#. Course enrollment
#. Publishing of final course grades
#. Automated creation of course shells on edX
#. Retrieve course attendance

Decision
========

We will introduce a new service called "registrar".  The primary purpose of this service is
the management of data related to a learner's enrollment in Master's (and eventually other types)
programs and courses therein.

- This service will explicitly persist student-program admission records (i.e. it
  records the fact that a student is enrolled in a program with some status).
- It will identify the courses in which the admitted student is enrolled in the
  pursuit of satisfying a program's requirements.
- It will serve as the primary integration point between partner Student Information Systems ("SIS")
  and edX systems.
- It will NOT explicitly capture the ways in which a program's requirements are satisfied
  (this is left to the partner's SIS).
- This service will communicate and synchronize data with other edX services
  via REST APIs.

  - Our initial synchronization strategy will likely be an ad-hoc strategy - we'll refresh
    data from other systems as needed, if it has not recently been refreshed (or if
    it is not currently persisted in registrar).

Status
======

Accepted (circa February 2019)

Consequences
============

- Registrar should be a "one-stop shop" for program third-parties/partners that need to integrate
  with the edX system.

  - Rather than having to integrate with the course-discovery service for some data needs
    and the LMS for other data needs, all program data integration can be done through one
    service, and the API specification to support third party needs can be captured
    within a single service and schema.

- We'll have explicit records representing the relationship between learners and (Master's) programs.

  - This will greatly simplify the ease with which we can reason about a learner's relationship
    to a program, which in turn simplifies business reporting along with the aforementioned
    integration with third parties.
  - We're trying to design the registrar service in such a way that it can be used to
    persist student-program enrollment data for other types of programs, too (e.g. MicroMasters).
    This would greatly enhance our business reporting capabilities.  It will also allow
    us to simplify the places throughout our systems that need to reason about a student's
    participation in a program.

- Why an independently-deployable application (IDA or "service")?

  - The business use-case captured above is a strong indicator that we're dealing with a bounded-context.
    While there is an up-front investment required in deploying new infrastructure, monitoring, and
    deployment pipelines, we'll get the classic benefits of an IDA:

    - Code integration and deployment that is not tied to a monolith (edx-platform/LMS).
    - Ease of integrating with third parties (like partners).
    - Ease of scaling.
    - Isolation of failure.

- Integration testing between registrar and other edX services comes to the fore.  This can help
  guide future decisions about a standard for integration testing between edX systems.
