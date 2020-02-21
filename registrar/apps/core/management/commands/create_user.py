""" Management command to create a user and add them to OrganizationGroups """
import logging

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from registrar.apps.core.models import User


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    help = 'Creates the specified user, if it does not exist, and sets its groups.'

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument('--email', default='')
        parser.add_argument('--superuser', dest='is_superuser', action='store_true')
        parser.add_argument('--staff', dest='is_staff', action='store_true')
        parser.add_argument('-g', '--groups', dest='group_names', nargs='*', default=[])

    # pylint: disable=arguments-differ
    @transaction.atomic
    def handle(self, username, email, is_superuser, is_staff, group_names, *args, **options):
        user = self.make_user(username, email, is_superuser, is_staff)
        groups = self.get_groups(group_names)
        if groups:
            self.add_user_to_groups(user, groups)

    def make_user(self, username, email, is_superuser, is_staff):
        try:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'is_superuser': is_superuser,
                    'is_staff': is_staff,
                }
            )
        except Exception as ex:
            raise CommandError('Unable to create User {}. Cause: {}'.format(username, ex))
        if not created:
            raise CommandError('User {} already exists'.format(user))
        logger.info("Created user: {}".format(user))
        return user

    def get_groups(self, group_names):
        if not group_names:
            return []
        group_set = set(group_names)
        if len(group_set) != len(group_names):
            raise CommandError('Duplicate groups not allowed')
        groups = []
        for group_name in group_names:
            try:
                group = Group.objects.get(name=group_name)
                groups.append(group)
            except Group.DoesNotExist:
                raise CommandError('Group {} does not exist'.format(group_name))
        return groups

    def add_user_to_groups(self, user, groups):
        try:
            user.groups.add(*groups)
        except Exception as ex:  # pragma: no cover
            raise CommandError('Unable to add user to groups. Cause: {}'.format(ex))
        logger.info('Added user {} to groups {}'.format(user, groups))
