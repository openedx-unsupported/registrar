# -*- coding: utf-8 -*-
# Generated by Django 1.11.25 on 2019-11-25 18:23
from __future__ import unicode_literals

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_jobpermissionsupport'),
    ]

    operations = [
        migrations.CreateModel(
            name='Program',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('key', models.CharField(max_length=255, unique=True)),
                ('discovery_uuid', models.UUIDField(db_index=True, null=True)),
                ('managing_organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.Organization')),
            ],
        ),
    ]
