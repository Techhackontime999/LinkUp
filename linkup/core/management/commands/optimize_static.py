"""
Management command to optimize static files for better performance.
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from core.static_optimization import optimize_static_files, generate_cache_manifest


class Command(BaseCommand):
    help = 'Optimize static files (CSS, JS, images) for better performance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--generate-manifest',
            action='store_true',
            help='Generate cache manifest for static files',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting static file optimization...')
        )

        # Optimize static files
        optimize_static_files()

        # Generate cache manifest if requested
        if options['generate_manifest']:
            self.stdout.write('Generating cache manifest...')
            manifest = generate_cache_manifest()
            if manifest:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Generated cache manifest with {len(manifest["files"])} files'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS('Static file optimization completed!')
        )