# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-12 02:52
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('signal', '0006_auto_20171206_1053'),
    ]

    operations = [
        migrations.RenameField(
            model_name='signal',
            old_name='base_coin',
            new_name='counter_currency',
        ),
        migrations.RenameField(
            model_name='signal',
            old_name='coin',
            new_name='transaction_currency',
        ),
    ]
