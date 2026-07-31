from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('estudiante', '0002_perfil'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Perfil',
        ),
    ]
