# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-05-24 15:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('info_bot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='infobothistory',
            name='chat_title',
            field=models.CharField(default='', max_length=256),
        ),
    ]