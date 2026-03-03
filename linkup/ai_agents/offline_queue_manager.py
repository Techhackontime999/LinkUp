"""
Offline message queue manager for AI agents.

This module handles queuing and delivery of messages when agents are offline.
"""
import logging
from typing import List, Dict, Any
from django.core.cache import cache
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import AIAgent, AgentMessage

logger = logging.getLogger(__name__)


class OfflineQueueManager:
    """
    Manages message queuing and delivery for offline agents.
    
    Features:
    - Queue messages when agents are offline
    - Deliver queued messages when agents come online
    - Track pending message counts
    - Handle delivery failures gracefully
    """
    
    @staticmethod
    def queue_message(message: AgentMessage) -> bool:
        """
        Add a message to the offline queue for a recipient.
        
        Args:
            message: AgentMessage instance to queue
        
        Returns:
            Boolean indicating success
        
        Requirements: 4.3, 13.5
        """
        try:
            recipient_id = str(message.recipient.id)
            queue_key = f'agent_offline_queue:{recipient_id}'
            
            # Get current queue
            queue = cache.get(queue_key, [])
            
            # Add message ID to queue
            queue.append(str(message.id))
            
            # Store queue with 7-day TTL
            cache.set(queue_key, queue, timeout=604800)
            
            logger.info(f"Message {message.id} queued for offline agent {recipient_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error queuing message: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_queued_messages(agent_id: str) -> List[AgentMessage]:
        """
        Get all queued messages for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            List of AgentMessage instances
        """
        try:
            queue_key = f'agent_offline_queue:{agent_id}'
            
            # Get message IDs from queue
            message_ids = cache.get(queue_key, [])
            
            if not message_ids:
                return []
            
            # Retrieve messages from database
            messages = AgentMessage.objects.filter(
                id__in=message_ids,
                recipient_id=agent_id
            ).order_by('created_at')
            
            return list(messages)
            
        except Exception as e:
            logger.error(f"Error retrieving queued messages: {e}", exc_info=True)
            return []
    
    @staticmethod
    def deliver_queued_messages(agent_id: str) -> Dict[str, Any]:
        """
        Deliver all queued messages to an agent when they come online.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Dictionary with delivery results
        
        Requirements: 4.3, 13.3
        """
        try:
            # Get queued messages
            messages = OfflineQueueManager.get_queued_messages(agent_id)
            
            if not messages:
                return {
                    'success': True,
                    'delivered': 0,
                    'failed': 0
                }
            
            channel_layer = get_channel_layer()
            
            if not channel_layer:
                logger.error("Channel layer not configured")
                return {
                    'success': False,
                    'error': 'Channel layer not configured'
                }
            
            delivered = 0
            failed = 0
            
            # Deliver each message
            for message in messages:
                try:
                    # Prepare message payload
                    payload = {
                        'type': 'agent_message',
                        'message_id': str(message.id),
                        'sender_id': str(message.sender.id),
                        'sender_name': message.sender.name,
                        'content': message.content,
                        'metadata': message.metadata,
                        'message_type': message.message_type,
                        'priority': message.priority,
                        'parent_message_id': str(message.parent_message.id) if message.parent_message else None,
                        'timestamp': message.created_at.isoformat()
                    }
                    
                    # Send via channel layer
                    channel_name = f'agent_{agent_id}'
                    async_to_sync(channel_layer.group_send)(
                        channel_name,
                        payload
                    )
                    
                    # Update message status
                    message.status = 'DELIVERED'
                    message.delivered_at = timezone.now()
                    
                    # Calculate latency
                    latency = (message.delivered_at - message.created_at).total_seconds() * 1000
                    message.latency_ms = int(latency)
                    
                    message.save()
                    
                    delivered += 1
                    
                except Exception as e:
                    logger.error(f"Error delivering queued message {message.id}: {e}", exc_info=True)
                    
                    # Update message status to FAILED
                    message.status = 'FAILED'
                    message.save()
                    
                    failed += 1
            
            # Clear the queue
            queue_key = f'agent_offline_queue:{agent_id}'
            cache.delete(queue_key)
            
            logger.info(f"Delivered {delivered} queued messages to agent {agent_id}, {failed} failed")
            
            return {
                'success': True,
                'delivered': delivered,
                'failed': failed
            }
            
        except Exception as e:
            logger.error(f"Error delivering queued messages: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    @staticmethod
    def get_queue_count(agent_id: str) -> int:
        """
        Get the number of queued messages for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Number of queued messages
        """
        try:
            queue_key = f'agent_offline_queue:{agent_id}'
            message_ids = cache.get(queue_key, [])
            return len(message_ids)
            
        except Exception as e:
            logger.error(f"Error getting queue count: {e}", exc_info=True)
            return 0
    
    @staticmethod
    def clear_queue(agent_id: str) -> bool:
        """
        Clear all queued messages for an agent.
        
        Args:
            agent_id: UUID of the agent
        
        Returns:
            Boolean indicating success
        """
        try:
            queue_key = f'agent_offline_queue:{agent_id}'
            cache.delete(queue_key)
            
            logger.info(f"Cleared message queue for agent {agent_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing queue: {e}", exc_info=True)
            return False
