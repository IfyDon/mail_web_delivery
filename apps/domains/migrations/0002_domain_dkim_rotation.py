from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domains', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='domain',
            name='dkim_rotation_pending',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='domain',
            name='dkim_rotated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
