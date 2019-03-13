"""
Factories for creating core data.
"""

import re
import factory
from django.contrib.auth import get_user_model
from registrar.apps.core.permissions import OrganizationReadMetadataRole
from registrar.apps.core.models import Organization, OrganizationGroup


# pylint: disable=missing-docstring


User = get_user_model()


USER_PASSWORD = 'password'


class UserFactory(factory.DjangoModelFactory):
    class Meta:
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


class StaffUserFactory(UserFactory):
    is_staff = True


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
