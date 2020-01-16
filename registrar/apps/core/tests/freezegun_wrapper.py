# pylint: skip-file

import freezegun


def freeze_time(*args, **kwargs):
    """
    Work around bug in pylint/pylint_django.

    Some package in the Pylint ecosystem has an unresolved bug
    (https://github.com/PyCQA/pylint-django/issues/105)
    that makes pylint crash whenever we use `freezegun.freeze_time`.

    My understanding is that something goes wrong when trying
    to infer the type of the `@freezegun.freeze_time` decorator.
    Having this wrapper function in a pylint-skipped file
    seems to stop the crash from happening,
    possibly by avoiding type inference on `@freezegun.freeze_time`.

    This `@freeze_time` function can be used exactly like
    the original `@freezegun.freeze_time` decorator.
    """
    return freezegun.freeze_time(*args, **kwargs)
