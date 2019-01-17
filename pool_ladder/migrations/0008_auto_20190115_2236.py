# Generated by Django 2.1.5 on 2019-01-15 22:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pool_ladder', '0007_auto_20190115_2223'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='match',
            options={'ordering': ['-challenge_time']},
        ),
        migrations.AddField(
            model_name='match',
            name='loser_rank',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='match',
            name='winner_rank',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
