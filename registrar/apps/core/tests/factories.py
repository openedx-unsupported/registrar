"""
Factories for creating core data.
"""

import re

import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from guardian.shortcuts import assign_perm

from ..models import (
    Organization,
    OrganizationGroup,
    PendingUserGroup,
    Program,
    ProgramOrganizationGroup,
)
from ..permissions import OrganizationReadMetadataRole, ProgramReadMetadataRole
from ..proxies import DiscoveryProgram


# pylint: disable=missing-docstring


User = get_user_model()


USER_PASSWORD = 'password'


class GroupFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = Group
        django_get_or_create = ('name',)

    name = factory.Sequence('group{0}'.format)

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        if extracted is None:
            return

        for permission in extracted:
            assign_perm(permission, self)


class UserFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = User

    username = factory.Sequence(lambda n: 'user_%d' % n)
    password = factory.PostGenerationMethodCall('set_password', USER_PASSWORD)
    is_active = True
    is_superuser = False
    is_staff = False
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    full_name = factory.LazyAttribute(lambda user: ' '.join((user.first_name, user.last_name)))

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        if extracted is None:
            return

        for group in extracted:
            self.groups.add(group)  # pylint: disable=no-member


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
    class Meta(object):
        model = Organization

    key = factory.LazyAttribute(lambda org: name_to_key(org.name))
    discovery_uuid = factory.Faker('uuid4')
    name = factory.Sequence(lambda n: "Test Organization " + str(n))


class ProgramFactory(factory.DjangoModelFactory):
    class Meta:
        model = Program

    key = factory.Sequence(lambda n: 'test-program-{}'.format(n))  # pylint: disable=unnecessary-lambda
    discovery_uuid = factory.Faker('uuid4')
    managing_organization = factory.SubFactory(OrganizationFactory)


class DiscoveryProgramFactory(ProgramFactory):
    class Meta:
        model = DiscoveryProgram


class OrganizationGroupFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = OrganizationGroup

    name = factory.LazyAttribute(
        lambda og: '{}_{}'.format(og.organization.key, og.role)
    )
    organization = factory.SubFactory(OrganizationFactory)
    role = OrganizationReadMetadataRole.name


class ProgramOrganizationGroupFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = ProgramOrganizationGroup

    name = factory.LazyAttribute(  # pragma: no cover
        lambda pg: '{}_{}'.format(pg.program.key, pg.role)
    )
    program = factory.SubFactory(ProgramFactory)
    granting_organization = factory.SubFactory(OrganizationFactory)
    role = ProgramReadMetadataRole.name


class PendingUserOrganizationGroupFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = PendingUserGroup

    group = factory.SubFactory(OrganizationGroupFactory)
    user_email = factory.Faker('email')


class PendingUserProgramGroupFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = PendingUserGroup

    group = factory.SubFactory(ProgramOrganizationGroupFactory)
    user_email = factory.Faker('email')


class PendingUserGenericGroupFactory(factory.DjangoModelFactory):
    class Meta(object):
        model = PendingUserGroup

    group = factory.SubFactory(GroupFactory)
    user_email = factory.Faker('email')
