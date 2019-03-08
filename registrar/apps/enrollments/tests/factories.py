"""
Factories for creating enrollment data.
"""
import re

import factory

from registrar.apps.enrollments.permissions import OrganizationReadMetadataRole
from registrar.apps.enrollments.models import (
    Organization,
    OrganizationGroup,
    Program,
)


# pylint: disable=missing-docstring


def name_to_key(name):
    """
    Returns a 'key-like' version of a name.

    Example:
        name_to_key("Master's in Computer Science") =>
            'masters-in-computer-science'
    """
    name2 = name.replace(' ', '-').replace('_', '-').lower()
    return re.sub(r'[^a-z0-9-]', '', name2)


class OrganizationFactory(factory.DjangoModelFactory):
    class Meta:
        model = Organization

    key = factory.LazyAttribute(lambda org: name_to_key(org.name))
    discovery_uuid = factory.Faker('uuid4')
    name = factory.Sequence(lambda n: "Test Origanization " + str(n))


class OrganizationGroupFactory(factory.DjangoModelFactory):
    class Meta:
        model = OrganizationGroup

    organization = factory.SubFactory(OrganizationFactory)
    role = OrganizationReadMetadataRole.name


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
