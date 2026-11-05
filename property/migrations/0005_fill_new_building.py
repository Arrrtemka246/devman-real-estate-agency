from django.db import migrations


def fill_new_building(apps, schema_editor):
    Flat = apps.get_model("property", "Flat")
    flats = Flat.objects.using(schema_editor.connection.alias)
    flats.filter(
        new_building__isnull=True,
        construction_year__gte=2015,
    ).update(new_building=True)
    flats.filter(new_building__isnull=True).update(new_building=False)


class Migration(migrations.Migration):
    dependencies = [("property", "0004_flat_new_building")]
    operations = [
        migrations.RunPython(fill_new_building, migrations.RunPython.noop),
    ]
