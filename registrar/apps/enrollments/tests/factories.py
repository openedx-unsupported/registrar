"""
Factories for creating enrollment data.
"""
import factory

from registrar.apps.core.utils import name_to_key
from registrar.apps.enrollments.models import (
    Program,
)


# pylint: disable=missing-docstring


class ProgramFactory(factory.DjangoModelFactory):
    class Meta:
        model = Program

    key = factory.LazyAttribute(lambda prg: name_to_key(prg.title))
    discovery_uuid = factory.Faker('uuid4')
    url = factory.LazyAttribute(
        lambda prg: 'https://{0}.edx.org/{1}'.format(
            prg.managing_organization.key, prg.key
        )
    )
