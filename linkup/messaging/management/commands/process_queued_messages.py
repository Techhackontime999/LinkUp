from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
import logging

from messaging.models import QueuedMessage, Message, UserStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process queued messages and attempt to deliver them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of messages to process in each batch'
        )
        parser.add_argument(
            '--max-age-hours',
            type=int,
            default=24,
            help='Maximum age of queued messages to process (in hours)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        max_age_hours = options['max_age_hours']
        
        # Calculate cutoff time
        cutoff_time = timezone.now() - timezone.timedelta(hours=max_age_hours)
        
        self.stdout.write(f"Processing queued messages (batch size: {batch_size}, max age: {max_age_hours}h)")
        
        # Get queued messages that can be retried
        queued_messages = QueuedMessage.objects.filter(
            is_processed=False,
            created_at__gte=cutoff_time
        ).select_related('sender', 'recipient')[:batch_size]
        
        processed_count = 0
        failed_count = 0
        
        channel_layer = get_channel_layer()
        
        for queued_msg in queued_messages:
            try:
                with transaction.atomic():
                    # Check if recipient is online
                    try:
                        recipient_status = UserStatus.objects.get(user=queued_msg.recipient)
                        is_recipient_online = recipient_status.is_online
                    except UserStatus.DoesNotExist:
                        is_recipient_online = False
                    
                    if queued_msg.can_retry():
                        # Create the actual message
                        message = Message.objects.create(
                            sender=queued_msg.sender,
                            recipient=queued_msg.recipient,
                            content=queued_msg.content
                        )
                        
                        # Try to send via WebSocket if recipient is online
                        if is_recipient_online and channel_layer:
                            try:
                                # Create message payload
                                payload = {
                                    'type': 'message',
                                    'id': message.id,
                                    'sender': message.sender.username,
                                    'recipient': message.recipient.username,
                                    'content': message.content,
                                    'created_at': message.created_at.isoformat(),
                                    'is_read': message.is_read,
                                    'read_at': message.read_at.isoformat() if message.read_at else None,
                                    'delivered_at': message.delivered_at.isoformat() if message.delivered_at else None,
                                }
                                
                                # Send to recipient's notification channel
                                async_to_sync(channel_layer.group_send)(
                                    f'user_{queued_msg.recipient.id}',
                                    {
                                        'type': 'notification',
                                        'message': payload,
                                    }
                                )
                                
                                # Mark as delivered
                                message.mark_as_delivered()
                                
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"Delivered queued message {queued_msg.id} to online user {queued_msg.recipient.username}"
                                    )
                                )
                                
                            except Exception as e:
                                logger.error(f"Failed to send WebSocket message for queued message {queued_msg.id}: {e}")
                                # Message is still created, just not delivered via WebSocket
                        
                        # Mark queued message as processed
                        queued_msg.mark_processed()
                        processed_count += 1
                        
                        self.stdout.write(f"Processed queued message {queued_msg.id}")
                        
                    else:
                        # Message has exceeded retry limit or is too old
                        queued_msg.is_processed = True
                        queued_msg.save(update_fields=['is_processed'])
                        failed_count += 1
                        
                        self.stdout.write(
                            self.style.WARNING(
                                f"Marked queued message {queued_msg.id} as failed (retry limit exceeded)"
                            )
                        )
                        
            except Exception as e:
                logger.error(f"Error processing queued message {queued_msg.id}: {e}")
                
                # Increment retry count
                queued_msg.retry_count += 1
                queued_msg.last_retry_at = timezone.now()
                queued_msg.save(update_fields=['retry_count', 'last_retry_at'])
                failed_count += 1
        
        # Clean up old processed messages
        old_processed = QueuedMessage.objects.filter(
            is_processed=True,
            created_at__lt=cutoff_time
        )
        deleted_count = old_processed.count()
        old_processed.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Completed processing: {processed_count} processed, {failed_count} failed, {deleted_count} old messages cleaned up"
            )
        )