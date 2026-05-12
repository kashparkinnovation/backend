"""
Management command to backfill raw_password for all existing users.

Since hashed passwords cannot be reversed, this command generates
a new random password for every user whose raw_password is currently
empty, updates both the hashed and raw fields, and prints a summary.

Usage:
    python manage.py backfill_raw_passwords
    python manage.py backfill_raw_passwords --password=MyDefault123  # set same password for all
"""

import random
import string
from django.core.management.base import BaseCommand
from apps.users.models import CustomUser


class Command(BaseCommand):
    help = 'Backfill raw_password for all users that do not have one yet.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Set this specific password for ALL users (instead of random). '
                 'Useful for dev/testing environments.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be done without making changes.',
        )

    def handle(self, *args, **options):
        fixed_password = options['password']
        dry_run = options['dry_run']

        users = CustomUser.objects.filter(raw_password='')
        total = users.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS('All users already have raw_password set. Nothing to do.'))
            return

        self.stdout.write(f'Found {total} user(s) without raw_password.')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made.'))

        updated = 0
        for user in users.iterator():
            if fixed_password:
                new_pw = fixed_password
            else:
                new_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

            if not dry_run:
                user.set_password(new_pw)
                user.raw_password = new_pw
                user.save(update_fields=['password', 'raw_password'])

            self.stdout.write(
                f'  {"[DRY]" if dry_run else "  ✓"} '
                f'{user.email or user.phone} (ID {user.id}) → {new_pw}'
            )
            updated += 1

        action = 'would be updated' if dry_run else 'updated'
        self.stdout.write(self.style.SUCCESS(f'\nDone. {updated} user(s) {action}.'))
