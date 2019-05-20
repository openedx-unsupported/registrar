"""
Factories for creating enrollment data.
"""
import factory

from registrar.apps.enrollments.models import Program


# pylint: disable=missing-docstring


class ProgramFactory(factory.DjangoModelFactory):
    class Meta:
        model = Program

    key = factory.Sequence(lambda n: 'test-program-{}'.format(n))  # pylint: disable=unnecessary-lambda
    discovery_uuid = factory.Faker('uuid4')
