# Generated by Django 3.1.7 on 2021-03-14 07:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20210314_1557'),
    ]

    operations = [
        migrations.AlterModelTable(
            name='user',
            table='tb_users',
        ),
    ]
