# Generated by Django 2.1.5 on 2019-04-16 21:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pool_ladder', '0012_auto_20190122_1634'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='match',
            options={'ordering': ['-challenge_time'], 'verbose_name_plural': 'matches'},
        ),
    ]
