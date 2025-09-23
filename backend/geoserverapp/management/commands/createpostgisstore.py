from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from geoserverapp.services.geoserver_service import GeoServerService

class Command(BaseCommand):
    help = 'Creates a PostGIS store in GeoServer'

    def add_arguments(self, parser):
        # Optional arguments to override settings
        parser.add_argument(
            '--store-name',
            type=str,
            help='Specify store name (overrides settings.py)',
        )
        parser.add_argument(
            '--workspace',
            type=str,
            help='Specify workspace name (overrides settings.py)',
        )

    def handle(self, *args, **options):
        try:
            service = GeoServerService()
            
            store_name = options.get('store_name')
            workspace = options.get('workspace')
            
            if store_name and workspace:
                self.stdout.write(f"Creating store '{store_name}' in workspace '{workspace}'...")
                result = service.create_postgis_store(store_name=store_name,workspace=workspace,db_params=None)
            elif store_name:
                default_ws = settings.GEOSERVER.get('DEFAULT_WORKSPACE')
                self.stdout.write(f"Creating store '{store_name}' in workspace '{default_ws}'...")
                result = service.create_postgis_store(workspace=default_ws,store_name=store_name)
            elif workspace:
                default_store = settings.GEOSERVER.get('DEFAULT_STORE')
                self.stdout.write(f"Creating store '{default_store}' in workspace '{workspace}'...")
                result = service.create_postgis_store(workspace=workspace,store_name=default_store)
            else:
                default_store = settings.GEOSERVER.get('DEFAULT_STORE')
                default_ws = settings.GEOSERVER.get('DEFAULT_WORKSPACE')
                self.stdout.write(f"Creating store '{default_store}' in workspace '{default_ws}' from settings...")
                result = service.create_postgis_store(workspace=default_ws,store_name=default_store)
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created store. Result: {result}'))
        
        except Exception as e:
            raise CommandError(f'Failed to create store: {str(e)}')