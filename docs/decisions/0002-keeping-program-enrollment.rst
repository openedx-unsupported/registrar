Keeping the Program Enrollment Source of Truth within Registrar
===============================================================

Context
=======

Question have been raised by the edX architecture team about the fact that we have Program Enrollment
explicitly stored in Registrar service. They have the following concerns:

*. Registrar service seems to be servicing the function of being an integration service between
   school's system with edX about program administration
*. Program Enrollment is an edX domain concept that would be used by edX specific components to 
   realize functionality such as learner program progress display.
*. If Program enrollment data is needed outside of Registrar from services like LMS or Credentials,
   the synchronization of the critical data might become a production issue difficult to resolve
   and maintain


Decision
========

After careful consideration, we made the decision to keep Program Enrollment table within 
Registrar service. The decision is made based on the following:

- We believe this is a reversible decision within the second half of FY19.
- Currently, we only have the business need to store learner explicit program enrollment, when the program
  is managed by degree conferring schools. Program Enrollment will be exclusively serving the Master 
  programs for now. We are not planning to alter the existing system and logic related to other 
  programs like Micromasters.
- We do not intend to store Non-Masters program enrollments into Registrar service at this time. When
  we design to combine management of Masters program with all other programs, we will consider the new host
  for program enrollment
- We don’t know how edX-portal, the UI for Masters student is going to need program enrollment data
- No immediate return of investment if we decide to invest all this effort into a new source of truth.


Status
======

Accepted (circa February 2019)

Consequences
============

- Plans to develop Registrar service will continue as planned
- A reminder to check back on this decision is set

