# landreg/management/commands/publish_pelak.py
from django.core.management.base import BaseCommand
from django.conf import settings
from geoserverapp.services.geoserver_service import GeoServerService
from landreg.models.flag import Flag

class Command(BaseCommand):
    help = "Publish Pelak layer to GeoServer"

    def handle(self, *args, **options):
        geoserver_service = GeoServerService()
        try:
            result = geoserver_service.pulish_layer(
                workspace=settings.GEOSERVER['DEFAULT_WORKSPACE'],
                store_name=settings.GEOSERVER['DEFAULT_STORE'],
                pg_table=Flag._meta.db_table,
                title=Flag._meta.db_table,
            )
            self.stdout.write(self.style.SUCCESS(f"Published Flag layer: {result}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to publish Flag layer: {e}"))
