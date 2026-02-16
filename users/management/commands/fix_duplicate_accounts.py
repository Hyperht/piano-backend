"""
Management command to fix MultipleObjectsReturned issues in social authentication
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialAccount, EmailAddress
from django.db.models import Count

User = get_user_model()


class Command(BaseCommand):
    help = 'Fix duplicate users and social accounts that cause MultipleObjectsReturned errors'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Checking for duplicate users and social accounts...'))
        
        # Check for duplicate emails
        duplicate_emails = User.objects.values('email').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicate_emails:
            self.stdout.write(self.style.WARNING(f'Found {len(duplicate_emails)} duplicate email(s)'))
            for dup in duplicate_emails:
                email = dup['email']
                users = User.objects.filter(email=email).order_by('date_joined')
                self.stdout.write(f'  Email: {email} - {dup["count"]} users')
                
                # Keep the first user, merge others
                primary_user = users.first()
                duplicate_users = users[1:]
                
                for user in duplicate_users:
                    # Transfer social accounts to primary user
                    SocialAccount.objects.filter(user=user).update(user=primary_user)
                    # Transfer email addresses
                    EmailAddress.objects.filter(user=user).update(user=primary_user)
                    # Delete duplicate user
                    self.stdout.write(f'    Merging user {user.id} into {primary_user.id}')
                    user.delete()
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate emails found'))
        
        # Check for duplicate social accounts
        duplicate_social = SocialAccount.objects.values('provider', 'uid').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicate_social:
            self.stdout.write(self.style.WARNING(f'Found {len(duplicate_social)} duplicate social account(s)'))
            for dup in duplicate_social:
                provider = dup['provider']
                uid = dup['uid']
                accounts = SocialAccount.objects.filter(
                    provider=provider, 
                    uid=uid
                ).order_by('id')
                
                self.stdout.write(f'  {provider} - {uid}: {dup["count"]} accounts')
                
                # Keep the first account, delete others
                primary_account = accounts.first()
                duplicate_accounts = accounts[1:]
                
                for account in duplicate_accounts:
                    self.stdout.write(f'    Deleting duplicate account {account.id}')
                    account.delete()
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate social accounts found'))
        
        # Check for duplicate email addresses
        duplicate_email_addresses = EmailAddress.objects.values('email').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        if duplicate_email_addresses:
            self.stdout.write(self.style.WARNING(f'Found {len(duplicate_email_addresses)} duplicate EmailAddress(es)'))
            for dup in duplicate_email_addresses:
                email = dup['email']
                email_addresses = EmailAddress.objects.filter(email=email).order_by('id')
                
                # Keep the verified one if exists, otherwise keep the first
                verified = email_addresses.filter(verified=True).first()
                if verified:
                    primary = verified
                else:
                    primary = email_addresses.first()
                
                duplicates = email_addresses.exclude(id=primary.id)
                
                for email_addr in duplicates:
                    self.stdout.write(f'    Deleting duplicate EmailAddress {email_addr.id}')
                    email_addr.delete()
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate email addresses found'))
        
        self.stdout.write(self.style.SUCCESS('✅ Database cleanup complete!'))
