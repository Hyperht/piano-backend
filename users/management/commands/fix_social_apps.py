from django.core.management.base import BaseCommand
from allauth.socialaccount.models import SocialApp

class Command(BaseCommand):
    help = 'Fixes MultipleObjectsReturned error by removing duplicate SocialApp entries'

    def handle(self, *args, **options):
        apps = SocialApp.objects.filter(provider='google')
        count = apps.count()
        
        self.stdout.write(f"Found {count} Google social apps.")
        
        if count > 1:
            self.stdout.write("Duplicates found! Removing extras...")
            # Keep the first one, delete the rest
            first_app = apps.first()
            duplicates = apps.exclude(pk=first_app.pk)
            
            for duplicate in duplicates:
                self.stdout.write(f"Deleting duplicate app: {duplicate} (ID: {duplicate.pk})")
                duplicate.delete()
                
            self.stdout.write(self.style.SUCCESS("Successfully removed duplicate social apps."))
        else:
            self.stdout.write(self.style.SUCCESS("No duplicates found. Your configuration looks correct."))

