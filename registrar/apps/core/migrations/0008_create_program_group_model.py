# -*- coding: utf-8 -*-
# Generated by Django 1.11.24 on 2020-01-10 21:45
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0008_alter_user_username_max_length'),
        ('core', '0007_add_read_reports_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramOrganizationGroup',
            fields=[
                ('group_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='auth.Group')),
                ('role', models.CharField(choices=[('program_read_metadata', 'Read Program Metadata Only'), ('program_read_enrollments', 'Read Program Enrollments Data'), ('program_read_write_enrollments', 'Read and Write Program Enrollments Data'), ('program_read_reports', 'Read Program Reports')], default='program_read_metadata', max_length=255)),
                ('granting_organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Organization')),
            ],
            options={
                'verbose_name': 'Program Group',
            },
            bases=('auth.group',),
        ),
        migrations.AlterModelOptions(
            name='program',
            options={'permissions': (('program_read_metadata', 'View program metadata'), ('program_read_enrollments', 'Read program enrollment data'), ('program_write_enrollments', 'Write program enrollment data'), ('program_read_reports', 'Read program reports data'))},
        ),
        migrations.AlterField(
            model_name='organizationgroup',
            name='role',
            field=models.CharField(choices=[('organization_read_metadata', 'Read Organization Metadata Only'), ('organization_read_enrollments', 'Read Organization Enrollments Data'), ('organization_read_write_enrollments', 'Read and Write Organization Enrollments Data'), ('organization_read_reports', 'Read Organization Reports')], default='organization_read_metadata', max_length=255),
        ),
        migrations.AddField(
            model_name='programorganizationgroup',
            name='program',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Program'),
        ),
    ]
