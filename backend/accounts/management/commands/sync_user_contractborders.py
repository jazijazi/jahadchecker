from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Sync user accessible contractborders from layer permissions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Sync specific user only',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Process users in batches',
        )
    
    def handle(self, *args, **options):
        if options['user_id']:
            # Sync specific user
            try:
                user = User.objects.get(id=options['user_id'])
                user.sync_accessible_contractborders()
                self.stdout.write(
                    self.style.SUCCESS(f'Synced ContractBorders for user {user.username}')
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User {options["user_id"]} not found')
                )
        else:
            # Sync all users
            users = User.objects.all()
            total = users.count()
            batch_size = options['batch_size']
            
            for i in range(0, total, batch_size):
                batch = users[i:i + batch_size]
                with transaction.atomic():
                    for user in batch:
                        user.sync_accessible_contractborders()
                
                self.stdout.write(f'Processed {min(i + batch_size, total)}/{total} users')
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully synced ContractBorders for all {total} users')
            )