from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from geoserverapp.services.geoserver_service import GeoServerService

class Command(BaseCommand):
    help = 'Creates a workspace in GeoServer'

    def add_arguments(self, parser):
        # Optional argument to override the workspace name from settings
        parser.add_argument(
            '--name',
            type=str,
            help='Specify workspace name (overrides settings.py)',
        )

    def handle(self, *args, **options):
        try:
            service = GeoServerService()
            
            workspace_name = options.get('name')
            if workspace_name:
                self.stdout.write(f"Creating workspace '{workspace_name}'...")
                result = service.create_workspace(workspace_name=workspace_name)
            else:
                default_wrokspace_name = settings.GEOSERVER.get('DEFAULT_WORKSPACE')
                self.stdout.write(f"Creating workspace '{default_wrokspace_name}' from settings...")
                result = service.create_workspace(workspace_name=default_wrokspace_name)
            
            self.stdout.write(self.style.SUCCESS(f'Successfully created workspace. Result: {result}'))
        
        except Exception as e:
            raise CommandError(f'Failed to create workspace: {str(e)}')