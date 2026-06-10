from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('suppressions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bounce',
            name='bounce_type',
            field=models.CharField(
                choices=[('hard', 'Hard (Permanent)'), ('soft', 'Soft (Transient)')],
                default='hard',
                max_length=10,
                db_index=True,
            ),
        ),
    ]
