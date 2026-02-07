from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Drop all test data from the database (keeps staff/superuser accounts)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt'
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            confirm = input(
                'This will delete ALL test data (users, posts, jobs, etc.) except staff/superuser accounts. '
                'Are you sure you want to continue? (yes/no): '
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        with transaction.atomic():
            self.stdout.write('Dropping test data...')
            
            # Import models here to avoid circular imports
            from feed.models import Post, Comment
            from jobs.models import Job, Application
            from network.models import Connection, Follow
            from messaging.models import Message, Notification, UserStatus, TypingStatus, QueuedMessage
            from users.models import Experience, Education, Report, Block

            # Count records before deletion
            user_count = User.objects.filter(is_staff=False, is_superuser=False).count()
            post_count = Post.objects.count()
            job_count = Job.objects.count()
            message_count = Message.objects.count()
            connection_count = Connection.objects.count()

            # Delete in correct order to avoid foreign key constraints
            self.stdout.write('Deleting messages and notifications...')
            Message.objects.all().delete()
            Notification.objects.all().delete()
            UserStatus.objects.all().delete()
            TypingStatus.objects.all().delete()
            QueuedMessage.objects.all().delete()

            self.stdout.write('Deleting posts and comments...')
            Comment.objects.all().delete()
            Post.objects.all().delete()

            self.stdout.write('Deleting jobs and applications...')
            Application.objects.all().delete()
            Job.objects.all().delete()

            self.stdout.write('Deleting connections and follows...')
            Connection.objects.all().delete()
            Follow.objects.all().delete()

            self.stdout.write('Deleting user profiles...')
            Experience.objects.all().delete()
            Education.objects.all().delete()
            Report.objects.all().delete()
            Block.objects.all().delete()

            self.stdout.write('Deleting test users...')
            deleted_users, _ = User.objects.filter(is_staff=False, is_superuser=False).delete()

            # Report summary
            self.stdout.write(self.style.SUCCESS('\n=== Test Data Cleanup Summary ==='))
            self.stdout.write(f'Users deleted: {deleted_users}')
            self.stdout.write(f'Posts deleted: {post_count}')
            self.stdout.write(f'Jobs deleted: {job_count}')
            self.stdout.write(f'Messages deleted: {message_count}')
            self.stdout.write(f'Connections deleted: {connection_count}')
            self.stdout.write(self.style.SUCCESS('\nAll test data has been successfully removed!'))
