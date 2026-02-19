from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('birthday', '0019_scheduledwish_channel'),
    ]

    operations = [
        migrations.AddField(
            model_name='communicationlog',
            name='direction',
            field=models.CharField(choices=[('Outbound', 'Outbound'), ('Inbound', 'Inbound')], default='Outbound', max_length=20),
        ),
        migrations.AddField(
            model_name='communicationlog',
            name='external_message_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='communicationlog',
            name='gateway_number',
            field=models.CharField(blank=True, help_text='Twilio number used for this SMS', max_length=30, null=True),
        ),
    ]
