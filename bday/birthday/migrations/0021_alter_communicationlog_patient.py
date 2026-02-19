from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('birthday', '0020_communicationlog_direction_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='communicationlog',
            name='patient',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='communications', to='birthday.patient'),
        ),
    ]
