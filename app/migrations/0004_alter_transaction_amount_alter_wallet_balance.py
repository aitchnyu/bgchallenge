# Generated by Django 4.0.4 on 2022-04-29 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_transaction'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='amount',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='balance',
            field=models.IntegerField(default=0),
        ),
    ]
