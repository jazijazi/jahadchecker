# landreg/management/commands/publish_pelak.py
from django.core.management.base import BaseCommand
from django.conf import settings
from geoserverapp.services.geoserver_service import GeoServerService
from landreg.models.pelak import Pelak

class Command(BaseCommand):
    help = "Publish Pelak layer to GeoServer"

    def handle(self, *args, **options):
        geoserver_service = GeoServerService()
        try:
            print(">>>>>>>>>>" , Pelak._meta.db_table)
            result = geoserver_service.pulish_layer(
                workspace=settings.GEOSERVER['DEFAULT_WORKSPACE'],
                store_name=settings.GEOSERVER['DEFAULT_STORE'],
                pg_table=Pelak._meta.db_table,
                title=Pelak._meta.db_table,
            )
            self.stdout.write(self.style.SUCCESS(f"Published Pelak layer: {result}"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to publish Pelak layer: {e}"))
