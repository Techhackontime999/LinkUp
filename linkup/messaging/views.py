import json
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseServerError
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_GET, require_POST
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.conf import settings
from .models import Message, UserStatus, Notification
from .notification_service import NotificationService
from .message_persistence_manager import message_persistence_manager
from core.performance import (
    performance_monitor, QueryOptimizer, OptimizedPaginator, 
    CacheManager, cache_result
)

# Set up logging
logger = logging.getLogger(__name__)
User = get_user_model()


@login_required
@require_GET
@performance_monitor
def unread_notifications(request):
    """Return count and preview list of unread messages and notifications with error handling"""
    try:
        from django.urls import reverse

        # Get unread messages count with optimized query
        unread_messages_query = Message.objects.filter(recipient=request.user, is_read=False)
        unread_messages_query = QueryOptimizer.optimize_message_queries(unread_messages_query)
        total_unread_messages = unread_messages_query.count()
        
        # Get unread notifications count
        notification_service = NotificationService()
        total_unread_notifications = notification_service.get_unread_count(request.user)
        
        # Get message previews with optimization
        message_previews = unread_messages_query.order_by('-created_at')[:5]
        
        # Get notification previews
        notification_previews = notification_service.get_notifications(
            user=request.user,
            limit=5,
            unread_only=True
        )
        
        data = {
            'messages': {
                'count': total_unread_messages,
                'items': []
            },
            'notifications': {
                'count': total_unread_notifications,
                'items': notification_previews
            },
            'total_unread': total_unread_messages + total_unread_notifications
        }
        
        # Process message previews
        for m in message_previews:
            try:
                message_data = {
                    'id': m.id,
                    'type': 'message',
                    'sender': m.sender.username,
                    'content': (m.content[:120] + '...') if m.content and len(m.content) > 120 else (m.content or ''),
                    'created_at': m.created_at.isoformat(),
                    'chat_url': reverse('messaging:chat_view', args=[m.sender.username])
                }
                data['messages']['items'].append(message_data)
            except Exception as e:
                logger.error(f"Error processing message {m.id} in unread_notifications: {e}")
                continue
        
        return JsonResponse(data)
    
    except Exception as e:
        logger.error(f"Error in unread_notifications for user {request.user.id}: {e}")
        return JsonResponse({
            'error': 'Unable to fetch notifications',
            'messages': {'count': 0, 'items': []},
            'notifications': {'count': 0, 'items': []},
            'total_unread': 0
        }, status=500)


@login_required
def chat_view(request, username):
    """Chat page with user status and comprehensive error handling"""
    try:
        target = get_object_or_404(User, username=username)
        
        if request.user == target:
            logger.warning(f"User {request.user.id} attempted to chat with themselves")
            return redirect('profile')
        
        # Get user status with error handling
        is_online = False
        last_seen = None
        
        try:
            status = UserStatus.objects.get(user=target)
            is_online = status.is_online
            last_seen = status.last_seen
        except UserStatus.DoesNotExist:
            logger.info(f"UserStatus not found for user {target.id}, creating default")
            try:
                UserStatus.objects.create(user=target, is_online=False)
            except IntegrityError:
                pass  # Status was created by another request
        except Exception as e:
            logger.error(f"Error fetching user status for {target.id}: {e}")
        
        return render(request, 'messaging/chat.html', {
            'target': target,
            'is_online': is_online,
            'last_seen': last_seen
        })
    
    except User.DoesNotExist:
        logger.warning(f"User {username} not found for chat_view")
        return render(request, 'messaging/user_not_found.html', {'username': username}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in chat_view for {username}: {e}")
        return render(request, 'messaging/error.html', {
            'error_message': 'Unable to load chat. Please try again.'
        }, status=500)


@login_required
@performance_monitor
def fetch_history(request, username):
    """Return message history with enhanced persistence manager and 50-message initial loading"""
    try:
        target = get_object_or_404(User, username=username)
        
        if request.user == target:
            return JsonResponse({
                'error': "Cannot fetch conversation with yourself"
            }, status=400)

        # Get pagination parameters with enhanced defaults
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))  # Default 50 messages for initial load
        before_id = request.GET.get('before_id')  # For loading older messages
        include_metadata = request.GET.get('include_metadata', 'true').lower() == 'true'
        
        # Validate page size with enhanced limits
        if page_size > 100:
            page_size = 100  # Maximum 100 messages per request
        elif page_size < 10:
            page_size = 10   # Minimum 10 messages per request
        
        # Use enhanced persistence manager for conversation loading
        try:
            conversation_data = message_persistence_manager.get_conversation_messages(
                user1_id=request.user.id,
                user2_id=target.id,
                limit=page_size,
                before_id=int(before_id) if before_id else None,
                include_metadata=include_metadata
            )
            
            messages = conversation_data.get('messages', [])
            has_more = conversation_data.get('has_more', False)
            metadata = conversation_data.get('metadata', {})
            
        except Exception as e:
            logger.error(f"Error fetching conversation with persistence manager: {e}")
            # Fallback to original implementation
            from django.db.models import Q

            # Build base query with optimization
            base_query = Message.objects.filter(
                (Q(sender=request.user) & Q(recipient=target)) |
                (Q(sender=target) & Q(recipient=request.user))
            )
            base_query = QueryOptimizer.optimize_message_queries(base_query)
            
            # If before_id is provided, get messages older than that message
            if before_id:
                try:
                    before_message = Message.objects.get(id=before_id)
                    base_query = base_query.filter(created_at__lt=before_message.created_at)
                except Message.DoesNotExist:
                    pass  # Ignore invalid before_id
            
            # Order by created_at descending for pagination, then reverse for display
            msgs_query = base_query.order_by('-created_at')
            
            # Use optimized paginator
            paginator = OptimizedPaginator(
                msgs_query, 
                per_page=page_size,
                optimize_func=QueryOptimizer.optimize_message_queries
            )
            
            try:
                page_obj = paginator.get_page(page)
                msgs = list(page_obj.object_list)
                msgs.reverse()  # Reverse to show oldest first
                has_more = page_obj.has_next()
            except Exception as e:
                logger.error(f"Error paginating messages: {e}")
                return JsonResponse({
                    'error': 'Unable to fetch message history'
                }, status=500)

            # Convert to message format
            messages = []
            for m in msgs:
                try:
                    message_data = {
                        'id': m.id,
                        'sender': m.sender.username,
                        'recipient': m.recipient.username,
                        'content': m.content,
                        'status': m.status,
                        'client_id': m.client_id,
                        'created_at': m.created_at.isoformat(),
                        'sent_at': m.sent_at.isoformat() if m.sent_at else None,
                        'delivered_at': m.delivered_at.isoformat() if m.delivered_at else None,
                        'read_at': m.read_at.isoformat() if m.read_at else None,
                        'is_read': m.is_read,
                        'retry_count': m.retry_count,
                        'status_icon': m.get_status_icon()
                    }
                    messages.append(message_data)
                except Exception as e:
                    logger.error(f"Error processing message {m.id} in fetch_history: {e}")
                    continue
            
            metadata = {}

        # Mark messages as read using persistence manager for atomic operations
        try:
            unread_message_ids = [
                msg['id'] for msg in messages 
                if msg['recipient'] == request.user.username and not msg['is_read']
            ]
            
            if unread_message_ids:
                message_persistence_manager.bulk_update_message_status(
                    unread_message_ids, 'read', request.user.id
                )
                
                # Update the messages in response to reflect read status
                for msg in messages:
                    if msg['id'] in unread_message_ids:
                        msg['is_read'] = True
                        msg['read_at'] = timezone.now().isoformat()
                        msg['status'] = 'read'
                        
        except Exception as e:
            logger.error(f"Error marking messages as read with persistence manager: {e}")
            # Continue even if read marking fails

        # Enhanced response with metadata and performance info
        response_data = {
            'messages': messages,
            'has_more': has_more,
            'count': len(messages),
            'requested_count': page_size,
            'performance': {
                'persistence_manager_used': 'conversation_data' in locals(),
                'fallback_used': 'conversation_data' not in locals() or not conversation_data.get('messages')
            }
        }
        
        # Add metadata if available and requested
        if include_metadata and metadata:
            response_data['metadata'] = metadata
        
        # Add pagination info for compatibility
        response_data['pagination'] = {
            'has_previous': page > 1,
            'has_next': has_more,
            'current_page': page,
            'page_size': page_size,
            'total_messages': metadata.get('total_messages', len(messages))
        }
        
        return JsonResponse(response_data)
    
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in fetch_history: {e}")
        return JsonResponse({'error': 'Unable to fetch message history'}, status=500)


@login_required
@require_POST
def send_message_fallback(request, username):
    """Fallback HTTP POST to send a message with enhanced status tracking"""
    try:
        target = get_object_or_404(User, username=username)
        
        if request.user == target:
            return JsonResponse({
                'error': "Cannot message yourself"
            }, status=400)

        # Parse message content
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid request data in send_message_fallback: {e}")
            return JsonResponse({'error': 'Invalid request format'}, status=400)

        text = data.get('message', '').strip()
        client_id = data.get('client_id', f"http_fallback_{timezone.now().timestamp()}")
        
        if not text:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        if len(text) > 5000:  # Reasonable message length limit
            return JsonResponse({'error': 'Message too long (max 5000 characters)'}, status=400)

        # Create message with enhanced status tracking
        try:
            from .message_status_manager import message_status_manager
            
            with transaction.atomic():
                # Check for duplicate client_id
                existing_message = Message.objects.filter(
                    sender=request.user,
                    client_id=client_id
                ).first()
                
                if existing_message:
                    logger.warning(f"Duplicate HTTP fallback message with client_id {client_id}")
                    return JsonResponse({
                        'id': existing_message.id,
                        'sender': existing_message.sender.username,
                        'recipient': existing_message.recipient.username,
                        'content': existing_message.content,
                        'status': existing_message.status,
                        'client_id': existing_message.client_id,
                        'created_at': existing_message.created_at.isoformat(),
                        'sent_at': existing_message.sent_at.isoformat() if existing_message.sent_at else None,
                        'delivered_at': existing_message.delivered_at.isoformat() if existing_message.delivered_at else None,
                        'fallback': True
                    })
                
                # Create new message
                m = Message.objects.create(
                    sender=request.user, 
                    recipient=target, 
                    content=text,
                    client_id=client_id,
                    status='pending'
                )
                
                # Update status to sent for HTTP fallback
                message_status_manager.update_message_status(m, 'sent')
                
                # Try to broadcast via WebSocket if possible
                try:
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    
                    channel_layer = get_channel_layer()
                    if channel_layer:
                        # Create room name (same logic as ChatConsumer)
                        a, b = sorted([request.user.id, target.id])
                        room_group_name = f'chat_{a}_{b}'
                        
                        # Create message payload
                        payload = {
                            'type': 'message',
                            'id': m.id,
                            'sender': m.sender.username,
                            'recipient': m.recipient.username,
                            'content': m.content,
                            'status': m.status,
                            'client_id': m.client_id,
                            'created_at': m.created_at.isoformat(),
                            'sent_at': m.sent_at.isoformat() if m.sent_at else None,
                            'delivered_at': m.delivered_at.isoformat() if m.delivered_at else None,
                            'is_read': m.is_read,
                            'status_icon': m.get_status_icon(),
                            'fallback': True
                        }
                        
                        # Broadcast to WebSocket room
                        async_to_sync(channel_layer.group_send)(room_group_name, {
                            'type': 'chat_message',
                            'message': payload
                        })
                        
                        logger.info(f"HTTP fallback message {m.id} broadcasted via WebSocket")
                        
                except Exception as ws_error:
                    logger.warning(f"Failed to broadcast HTTP fallback message via WebSocket: {ws_error}")
                
                response_data = {
                    'id': m.id,
                    'sender': m.sender.username,
                    'recipient': m.recipient.username,
                    'content': m.content,
                    'status': m.status,
                    'client_id': m.client_id,
                    'created_at': m.created_at.isoformat(),
                    'sent_at': m.sent_at.isoformat() if m.sent_at else None,
                    'delivered_at': m.delivered_at.isoformat() if m.delivered_at else None,
                    'fallback': True
                }
                
                logger.info(f"Message sent via HTTP fallback from {request.user.id} to {target.id}")
                return JsonResponse(response_data)
                
        except ValidationError as e:
            logger.warning(f"Validation error in send_message_fallback: {e}")
            return JsonResponse({'error': 'Invalid message data'}, status=400)
        except IntegrityError as e:
            logger.error(f"Database integrity error in send_message_fallback: {e}")
            return JsonResponse({'error': 'Unable to send message'}, status=500)
    
    except User.DoesNotExist:
        return JsonResponse({'error': 'Recipient not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in send_message_fallback: {e}")
        return JsonResponse({'error': 'Unable to send message'}, status=500)


@login_required
@performance_monitor
def messages_inbox(request):
    """Display all conversations for the current user with error handling"""
    try:
        from django.db.models import Q, Max
        
        # Get unique users the current user has conversed with
        conversations = []
        seen_users = set()
        
        try:
            # Optimized query to get conversations
            messages_query = Message.objects.filter(
                Q(sender=request.user) | Q(recipient=request.user)
            )
            messages_query = QueryOptimizer.optimize_message_queries(messages_query)
            messages = messages_query.order_by('-created_at')
        except Exception as e:
            logger.error(f"Error fetching messages for inbox: {e}")
            messages = []
        
        for msg in messages:
            try:
                other_user = msg.recipient if msg.sender == request.user else msg.sender
                if other_user.id not in seen_users:
                    seen_users.add(other_user.id)
                    
                    # Get unread count with optimized query
                    try:
                        unread_count = Message.objects.filter(
                            sender=other_user, 
                            recipient=request.user, 
                            is_read=False
                        ).count()
                    except Exception as e:
                        logger.error(f"Error counting unread messages: {e}")
                        unread_count = 0
                    
                    # Get user status with caching
                    cache_key = CacheManager.get_cache_key('user_status', other_user.id)
                    cached_status = CacheManager.get_cached_user_profile(other_user.id)
                    
                    is_online = False
                    last_seen = None
                    
                    if not cached_status:
                        try:
                            status = UserStatus.objects.get(user=other_user)
                            is_online = status.is_online
                            last_seen = status.last_seen
                            
                            # Cache the status
                            status_data = {'is_online': is_online, 'last_seen': last_seen}
                            CacheManager.cache_user_profile(other_user.id, status_data)
                        except UserStatus.DoesNotExist:
                            pass
                        except Exception as e:
                            logger.error(f"Error fetching user status in inbox: {e}")
                    else:
                        is_online = cached_status.get('is_online', False)
                        last_seen = cached_status.get('last_seen')
                    
                    conversations.append({
                        'user': other_user,
                        'last_message': msg,
                        'unread_count': unread_count,
                        'is_online': is_online,
                        'last_seen': last_seen
                    })
            except Exception as e:
                logger.error(f"Error processing conversation in inbox: {e}")
                continue
        
        # Implement optimized pagination
        paginator = OptimizedPaginator(conversations, per_page=20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'messaging/inbox.html', {
            'page_obj': page_obj,
            'conversations': page_obj.object_list,
            'total_conversations': len(conversations)
        })
    
    except Exception as e:
        logger.error(f"Unexpected error in messages_inbox: {e}")
        # For debugging, show the actual error in development
        if settings.DEBUG:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Full traceback: {error_details}")
            return render(request, 'messaging/error.html', {
                'error_message': f'Debug Error: {str(e)}'
            }, status=500)
        else:
            return render(request, 'messaging/error.html', {
                'error_message': 'Unable to load inbox. Please try again.'
            }, status=500)


@login_required
@require_GET
def load_older_messages(request, username):
    """Enhanced load older messages using persistence manager for improved performance"""
    try:
        target = get_object_or_404(User, username=username)
        
        if request.user == target:
            return JsonResponse({
                'error': "Cannot fetch conversation with yourself"
            }, status=400)
        
        # Get parameters with enhanced validation
        before_id = request.GET.get('before_id')
        page_size = int(request.GET.get('page_size', 20))  # Default 20 messages per batch
        
        # Validate and limit page size for performance
        if page_size > 50:
            page_size = 50  # Maximum 50 messages per infinite scroll request
        elif page_size < 5:
            page_size = 5   # Minimum 5 messages per request
        
        if not before_id:
            return JsonResponse({'error': 'before_id parameter is required'}, status=400)
        
        try:
            before_id = int(before_id)
        except ValueError:
            return JsonResponse({'error': 'Invalid before_id format'}, status=400)
        
        # Use persistence manager for optimized message loading
        try:
            conversation_data = message_persistence_manager.get_conversation_messages(
                user1_id=request.user.id,
                user2_id=target.id,
                limit=page_size,
                before_id=before_id,
                include_metadata=False  # Don't need metadata for older messages
            )
            
            messages = conversation_data.get('messages', [])
            has_more = conversation_data.get('has_more', False)
            
        except Exception as e:
            logger.error(f"Error loading older messages with persistence manager: {e}")
            # Fallback to original implementation
            from django.db.models import Q
            
            try:
                before_message = Message.objects.get(id=before_id)
            except Message.DoesNotExist:
                return JsonResponse({'error': 'Invalid before_id'}, status=400)
            
            # Enhanced query with optimization
            try:
                base_query = Message.objects.filter(
                    (Q(sender=request.user) & Q(recipient=target)) |
                    (Q(sender=target) & Q(recipient=request.user)),
                    created_at__lt=before_message.created_at
                )
                
                # Apply query optimization
                base_query = QueryOptimizer.optimize_message_queries(base_query)
                
                # Fetch messages with proper ordering
                msgs = base_query.order_by('-created_at')[:page_size]
                
                # Convert to list and reverse to show oldest first
                msgs = list(msgs)
                msgs.reverse()
                
                # Convert to message format
                messages = []
                for m in msgs:
                    try:
                        message_data = {
                            'id': m.id,
                            'sender': m.sender.username,
                            'recipient': m.recipient.username,
                            'content': m.content,
                            'status': m.status,
                            'client_id': m.client_id,
                            'created_at': m.created_at.isoformat(),
                            'sent_at': m.sent_at.isoformat() if m.sent_at else None,
                            'delivered_at': m.delivered_at.isoformat() if m.delivered_at else None,
                            'read_at': m.read_at.isoformat() if m.read_at else None,
                            'is_read': m.is_read,
                            'retry_count': m.retry_count,
                            'status_icon': m.get_status_icon()
                        }
                        messages.append(message_data)
                    except Exception as e:
                        logger.error(f"Error processing message {m.id} in load_older_messages: {e}")
                        continue
                
                # Enhanced check for more messages with performance optimization
                has_more = False
                if messages:
                    oldest_loaded_time = msgs[0].created_at
                    
                    # Use exists() for better performance
                    has_more = Message.objects.filter(
                        (Q(sender=request.user) & Q(recipient=target)) |
                        (Q(sender=target) & Q(recipient=request.user)),
                        created_at__lt=oldest_loaded_time
                    ).exists()
                
            except Exception as e:
                logger.error(f"Error fetching older messages: {e}")
                return JsonResponse({
                    'error': 'Unable to fetch older messages'
                }, status=500)

        # Enhanced response with performance metrics
        response_data = {
            'messages': messages,
            'has_more': has_more,
            'loaded_count': len(messages),
            'requested_count': page_size,
            'performance': {
                'persistence_manager_used': 'conversation_data' in locals(),
                'fallback_used': 'conversation_data' not in locals() or not conversation_data.get('messages'),
                'query_optimized': True
            }
        }
        
        # Add pagination metadata for better client-side handling
        if messages:
            response_data['pagination'] = {
                'oldest_message_id': messages[0]['id'],
                'newest_message_id': messages[-1]['id'],
                'oldest_timestamp': messages[0]['created_at'],
                'newest_timestamp': messages[-1]['created_at']
            }
        
        return JsonResponse(response_data)
    
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except ValueError as e:
        logger.warning(f"Invalid parameter in load_older_messages: {e}")
        return JsonResponse({'error': 'Invalid parameters'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in load_older_messages: {e}")
        return JsonResponse({'error': 'Unable to load older messages'}, status=500)


@login_required
@require_GET
def synchronize_conversation(request, username):
    """Synchronize conversation data across tabs and devices using persistence manager"""
    try:
        target = get_object_or_404(User, username=username)
        
        if request.user == target:
            return JsonResponse({
                'error': "Cannot synchronize conversation with yourself"
            }, status=400)
        
        # Get last sync time parameter
        last_sync_param = request.GET.get('last_sync_time')
        last_sync_time = None
        
        if last_sync_param:
            try:
                from datetime import datetime
                last_sync_time = datetime.fromisoformat(last_sync_param.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Invalid last_sync_time format: {last_sync_param}")
        
        # Use persistence manager for synchronization
        try:
            sync_result = message_persistence_manager.synchronize_conversation(
                user_id=request.user.id,
                partner_id=target.id,
                last_sync_time=last_sync_time
            )
            
            return JsonResponse({
                'success': True,
                'sync_result': sync_result
            })
            
        except Exception as e:
            logger.error(f"Error synchronizing conversation: {e}")
            return JsonResponse({
                'error': 'Unable to synchronize conversation',
                'details': str(e) if logger.isEnabledFor(logging.DEBUG) else None
            }, status=500)
    
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in synchronize_conversation: {e}")
        return JsonResponse({'error': 'Unable to synchronize conversation'}, status=500)


@login_required
@require_GET
def user_status(request, username):
    """Get user online/offline status with error handling"""
    try:
        target = get_object_or_404(User, username=username)
        
        try:
            status = UserStatus.objects.get(user=target)
            return JsonResponse({
                'username': target.username,
                'is_online': status.is_online,
                'last_seen': status.last_seen.isoformat() if status.last_seen else None
            })
        except UserStatus.DoesNotExist:
            # Create default status
            try:
                UserStatus.objects.create(user=target, is_online=False)
            except IntegrityError:
                pass  # Status was created by another request
            
            return JsonResponse({
                'username': target.username,
                'is_online': False,
                'last_seen': None
            })
    
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in user_status for {username}: {e}")
        return JsonResponse({'error': 'Unable to fetch user status'}, status=500)


@login_required
@require_POST
def queue_message(request, username):
    """Queue a message for later delivery when WebSocket is unavailable"""
    try:
        target = get_object_or_404(User, username=username)
        
        if request.user == target:
            return JsonResponse({
                'error': "Cannot message yourself"
            }, status=400)

        # Parse message content
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body.decode('utf-8'))
            else:
                data = request.POST
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid request data in queue_message: {e}")
            return JsonResponse({'error': 'Invalid request format'}, status=400)

        text = data.get('message', '').strip()
        if not text:
            return JsonResponse({'error': 'Message content is required'}, status=400)
        
        if len(text) > 5000:  # Reasonable message length limit
            return JsonResponse({'error': 'Message too long (max 5000 characters)'}, status=400)

        # Queue the message
        try:
            from .models import QueuedMessage
            
            with transaction.atomic():
                queued_msg = QueuedMessage.objects.create(
                    sender=request.user,
                    recipient=target,
                    content=text
                )
                
                response_data = {
                    'id': f'queued_{queued_msg.id}',
                    'sender': request.user.username,
                    'recipient': target.username,
                    'content': text,
                    'created_at': queued_msg.created_at.isoformat(),
                    'queued': True,
                    'queue_id': queued_msg.id
                }
                
                logger.info(f"Message queued from {request.user.id} to {target.id}")
                return JsonResponse(response_data)
                
        except ValidationError as e:
            logger.warning(f"Validation error in queue_message: {e}")
            return JsonResponse({'error': 'Invalid message data'}, status=400)
        except IntegrityError as e:
            logger.error(f"Database integrity error in queue_message: {e}")
            return JsonResponse({'error': 'Unable to queue message'}, status=500)
    
    except User.DoesNotExist:
        return JsonResponse({'error': 'Recipient not found'}, status=404)
    except Exception as e:
        logger.error(f"Unexpected error in queue_message: {e}")
        return JsonResponse({'error': 'Unable to queue message'}, status=500)


@login_required
@require_POST
def mark_messages_read(request, username):
    """Mark all messages from a specific user as read"""
    try:
        target = get_object_or_404(User, username=username)
        
        with transaction.atomic():
            unread_messages = Message.objects.filter(
                sender=target,
                recipient=request.user,
                is_read=False
            ).select_for_update()
            
            count = 0
            for msg in unread_messages:
                msg.mark_as_read()
                count += 1
            
            return JsonResponse({
                'success': True,
                'marked_read': count
            })
    
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        logger.error(f"Error marking messages as read: {e}")
        return JsonResponse({'error': 'Unable to mark messages as read'}, status=500)


@login_required
@require_GET
def notifications_list(request):
    """Get paginated list of notifications for the user"""
    try:
        notification_service = NotificationService()
        
        # Get pagination parameters
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100 per request
        offset = int(request.GET.get('offset', 0))
        notification_type = request.GET.get('type')
        unread_only = request.GET.get('unread_only', '').lower() == 'true'
        
        notifications = notification_service.get_notifications(
            user=request.user,
            limit=limit,
            offset=offset,
            notification_type=notification_type,
            unread_only=unread_only
        )
        
        total_unread = notification_service.get_unread_count(request.user)
        
        return JsonResponse({
            'notifications': notifications,
            'total_unread': total_unread,
            'limit': limit,
            'offset': offset,
            'has_more': len(notifications) == limit  # Indicates if there might be more
        })
    
    except Exception as e:
        logger.error(f"Error getting notifications list: {e}")
        return JsonResponse({'error': 'Unable to fetch notifications'}, status=500)


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification_service = NotificationService()
        success = notification_service.mark_notification_read(notification_id, request.user)
        
        if success:
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Notification not found'}, status=404)
    
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return JsonResponse({'error': 'Unable to mark notification as read'}, status=500)


@login_required
@require_POST
def mark_all_notifications_read(request):
    """Mark all notifications as read for the user"""
    try:
        notification_service = NotificationService()
        
        # Optional filter by notification type
        notification_type = request.POST.get('notification_type')
        
        count = notification_service.mark_all_read(request.user, notification_type)
        
        return JsonResponse({
            'success': True,
            'marked_count': count
        })
    
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return JsonResponse({'error': 'Unable to mark notifications as read'}, status=500)


@login_required
@require_GET
def notification_preferences(request):
    """Get user's notification preferences"""
    try:
        from .models import NotificationPreference
        
        preferences = NotificationPreference.objects.filter(user=request.user)
        
        # Create default preferences for missing types
        all_types = [choice[0] for choice in Notification.NOTIFICATION_TYPES]
        existing_types = set(pref.notification_type for pref in preferences)
        
        for notification_type in all_types:
            if notification_type not in existing_types:
                NotificationPreference.objects.get_or_create(
                    user=request.user,
                    notification_type=notification_type,
                    defaults={
                        'delivery_method': 'realtime',
                        'is_enabled': True
                    }
                )
        
        # Refresh preferences
        preferences = NotificationPreference.objects.filter(user=request.user)
        
        data = []
        for pref in preferences:
            data.append({
                'notification_type': pref.notification_type,
                'notification_type_display': pref.get_notification_type_display(),
                'delivery_method': pref.delivery_method,
                'delivery_method_display': pref.get_delivery_method_display(),
                'is_enabled': pref.is_enabled,
                'quiet_hours_start': pref.quiet_hours_start.strftime('%H:%M') if pref.quiet_hours_start else None,
                'quiet_hours_end': pref.quiet_hours_end.strftime('%H:%M') if pref.quiet_hours_end else None,
            })
        
        return JsonResponse({'preferences': data})
    
    except Exception as e:
        logger.error(f"Error getting notification preferences: {e}")
        return JsonResponse({'error': 'Unable to fetch preferences'}, status=500)


@login_required
@require_POST
def update_notification_preferences(request):
    """Update user's notification preferences"""
    try:
        from .models import NotificationPreference
        import json
        
        data = json.loads(request.body)
        preferences_data = data.get('preferences', [])
        
        updated_count = 0
        for pref_data in preferences_data:
            notification_type = pref_data.get('notification_type')
            if not notification_type:
                continue
            
            pref, created = NotificationPreference.objects.get_or_create(
                user=request.user,
                notification_type=notification_type
            )
            
            # Update fields
            if 'delivery_method' in pref_data:
                pref.delivery_method = pref_data['delivery_method']
            if 'is_enabled' in pref_data:
                pref.is_enabled = pref_data['is_enabled']
            if 'quiet_hours_start' in pref_data:
                from datetime import datetime
                if pref_data['quiet_hours_start']:
                    pref.quiet_hours_start = datetime.strptime(pref_data['quiet_hours_start'], '%H:%M').time()
                else:
                    pref.quiet_hours_start = None
            if 'quiet_hours_end' in pref_data:
                from datetime import datetime
                if pref_data['quiet_hours_end']:
                    pref.quiet_hours_end = datetime.strptime(pref_data['quiet_hours_end'], '%H:%M').time()
                else:
                    pref.quiet_hours_end = None
            
            pref.save()
            updated_count += 1
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count
        })
    
    except Exception as e:
        logger.error(f"Error updating notification preferences: {e}")
        return JsonResponse({'error': 'Unable to update preferences'}, status=500)


@login_required
@require_GET
def notification_preferences_page(request):
    """Render the notification preferences page"""
    return render(request, 'messaging/notification_preferences.html')


@login_required
@require_GET
def notification_dashboard(request):
    """Render the notification dashboard (admin only)"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Access denied")
    return render(request, 'messaging/notification_dashboard.html')