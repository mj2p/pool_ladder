# Generated by Django 2.1.5 on 2019-01-20 22:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pool_ladder', '0010_auto_20190118_1600'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='match',
            options={'ordering': ['-challenge_time'], 'verbose_name_plural': 'matches'},
        ),
        migrations.AddField(
            model_name='userprofile',
            name='movement',
            field=models.IntegerField(default=0),
        ),
    ]