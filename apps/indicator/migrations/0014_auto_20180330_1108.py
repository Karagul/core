# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-03-30 11:08
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indicator', '0013_auto_20180330_0936'),
    ]

    operations = [
        migrations.AlterField(
            model_name='annpriceclassification',
            name='predicted_ahead_for',
            field=models.SmallIntegerField(null=True),
        ),
    ]
