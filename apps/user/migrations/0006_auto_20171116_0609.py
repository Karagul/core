# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-11-16 06:09
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0005_auto_20171115_0828'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='_beta_subscription_token',
            field=models.CharField(default='', max_length=8),
        ),
    ]
