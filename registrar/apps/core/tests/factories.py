"""
Factories for creating core data.
"""

from django.contrib.auth import get_user_model
import factory


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
