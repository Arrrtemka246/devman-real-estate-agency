from django.db import migrations


def link_owners(apps, schema_editor):
    Flat = apps.get_model("property", "Flat")
    Owner = apps.get_model("property", "Owner")
    Ownership = Owner.flats.through
    alias = schema_editor.connection.alias
    owners = {
        (owner.name, str(owner.phonenumber or ""), owner.source_phone): owner.pk
        for owner in Owner.objects.using(alias).all().iterator()
    }
    batch = []
    for flat in Flat.objects.using(alias).all().iterator(chunk_size=1000):
        key = (
            flat.owner,
            str(flat.owner_pure_phone or ""),
            flat.owners_phonenumber,
        )
        batch.append(Ownership(flat_id=flat.pk, owner_id=owners[key]))
        if len(batch) == 1000:
            Ownership.objects.using(alias).bulk_create(
                batch,
                ignore_conflicts=True,
            )
            batch = []
    if batch:
        Ownership.objects.using(alias).bulk_create(batch, ignore_conflicts=True)


class Migration(migrations.Migration):
    dependencies = [("property", "0009_copy_owners")]
    operations = [
        migrations.RunPython(link_owners, migrations.RunPython.noop),
    ]
