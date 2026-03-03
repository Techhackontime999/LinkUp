"""
Research Analytics Engine for analyzing AI agent interaction patterns and generating insights.

This module provides comprehensive analytics capabilities for the AI-to-AI interaction platform,
including temporal analytics, pattern detection, thread-level analytics, and metric storage.
"""
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from django.db import models
from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from .models import AIAgent, AgentMessage, AgentInteraction, ResearchMetric


class ResearchAnalyticsEngine:
    """
    Service for analyzing interaction patterns and generating insights.
    
    This service handles:
    - Calculating interaction statistics (frequency, duration, patterns)
    - Temporal analytics (hourly, daily, weekly aggregation)
    - Pattern detection (conversation style, response patterns)
    - Thread-level analytics
    - Metric storage in ResearchMetric table
    
    Requirements: 7.1-7.8, 17.4-17.5, 19.1-19.5
    """
    
    @staticmethod
    def calculate_metrics(
        agent_id: str,
        time_range: Dict[str, datetime],
        metric_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics for an agent over a time range.
        
        Args:
            agent_id: UUID of the agent
            time_range: Dictionary with 'start_time' and 'end_time' datetime objects
            metric_types: Optional list of specific metrics to calculate
                         (if None, calculates all metrics)
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - metrics: Dictionary of calculated metrics
                - error: Error message (on failure)
        
        Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
        """
        try:
            # Validate agent exists
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Validate time range
            start_time = time_range.get('start_time')
            end_time = time_range.get('end_time')
            
            if not start_time or not end_time:
                return {
                    'status': 'FAILED',
                    'error': 'Time range must include start_time and end_time'
                }
            
            if start_time >= end_time:
                return {
                    'status': 'FAILED',
                    'error': 'start_time must be before end_time'
                }
            
            # Initialize metrics dictionary
            metrics = {}
            
            # Determine which metrics to calculate
            all_metrics = metric_types is None
            
            # Calculate basic message metrics (Requirement 7.1)
            if all_metrics or 'message_counts' in metric_types:
                message_metrics = ResearchAnalyticsEngine._calculate_message_counts(
                    agent, start_time, end_time
                )
                metrics.update(message_metrics)
            
            # Identify unique conversation partners (Requirement 7.2)
            if all_metrics or 'conversation_partners' in metric_types:
                partner_metrics = ResearchAnalyticsEngine._calculate_conversation_partners(
                    agent, start_time, end_time
                )
                metrics.update(partner_metrics)
            
            # Calculate average response time (Requirement 7.3)
            if all_metrics or 'response_time' in metric_types:
                response_metrics = ResearchAnalyticsEngine._calculate_response_time(
                    agent, start_time, end_time
                )
                metrics.update(response_metrics)
            
            # Generate message frequency distribution (Requirement 7.4)
            if all_metrics or 'frequency_distribution' in metric_types:
                frequency_metrics = ResearchAnalyticsEngine._calculate_frequency_distribution(
                    agent, start_time, end_time
                )
                metrics.update(frequency_metrics)
            
            # Identify peak activity hours (Requirement 7.5)
            if all_metrics or 'peak_hours' in metric_types:
                peak_metrics = ResearchAnalyticsEngine._calculate_peak_hours(
                    metrics.get('message_frequency_per_hour', {})
                )
                metrics.update(peak_metrics)
            
            # Detect conversation patterns (Requirement 7.6)
            if all_metrics or 'patterns' in metric_types:
                pattern_metrics = ResearchAnalyticsEngine._detect_patterns(
                    agent, start_time, end_time
                )
                metrics.update(pattern_metrics)
            
            return {
                'status': 'SUCCESS',
                'metrics': metrics
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.analytics')
            logger.error(f'Failed to calculate metrics: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def _calculate_message_counts(
        agent: AIAgent,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, int]:
        """
        Calculate total messages sent and received.
        
        Requirement: 7.1
        """
        sent_count = AgentMessage.objects.filter(
            sender=agent,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        received_count = AgentMessage.objects.filter(
            recipient=agent,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).count()
        
        return {
            'total_messages_sent': sent_count,
            'total_messages_received': received_count,
            'total_messages': sent_count + received_count
        }
    
    @staticmethod
    def _calculate_conversation_partners(
        agent: AIAgent,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Identify unique conversation partners.
        
        Requirement: 7.2
        """
        # Get unique recipients from sent messages
        sent_partners = set(
            AgentMessage.objects.filter(
                sender=agent,
                created_at__gte=start_time,
                created_at__lte=end_time
            ).values_list('recipient_id', flat=True).distinct()
        )
        
        # Get unique senders from received messages
        received_partners = set(
            AgentMessage.objects.filter(
                recipient=agent,
                created_at__gte=start_time,
                created_at__lte=end_time
            ).values_list('sender_id', flat=True).distinct()
        )
        
        # Combine both sets
        all_partners = sent_partners.union(received_partners)
        
        return {
            'unique_conversation_partners': len(all_partners),
            'conversation_partner_ids': [str(pid) for pid in all_partners]
        }
    
    @staticmethod
    def _calculate_response_time(
        agent: AIAgent,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Calculate average response time between received and sent messages.
        
        Requirement: 7.3
        """
        # Get all received messages in time range
        received_messages = AgentMessage.objects.filter(
            recipient=agent,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).order_by('created_at')
        
        response_times = []
        
        for received_msg in received_messages:
            # Find the next sent message to the same agent within 60 minutes
            response = AgentMessage.objects.filter(
                sender=agent,
                recipient=received_msg.sender,
                created_at__gt=received_msg.created_at,
                created_at__lte=received_msg.created_at + timedelta(minutes=60)
            ).order_by('created_at').first()
            
            if response:
                # Calculate response time in milliseconds
                response_time = (response.created_at - received_msg.created_at).total_seconds() * 1000
                response_times.append(response_time)
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
        else:
            avg_response_time = 0
            min_response_time = 0
            max_response_time = 0
        
        return {
            'average_response_time_ms': avg_response_time,
            'min_response_time_ms': min_response_time,
            'max_response_time_ms': max_response_time,
            'response_count': len(response_times)
        }
    
    @staticmethod
    def _calculate_frequency_distribution(
        agent: AIAgent,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Generate message frequency distribution by hour.
        
        Requirement: 7.4
        """
        # Initialize hour buckets (0-23)
        hour_buckets = {hour: 0 for hour in range(24)}
        
        # Get all messages (sent and received)
        sent_messages = AgentMessage.objects.filter(
            sender=agent,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).values_list('created_at', flat=True)
        
        received_messages = AgentMessage.objects.filter(
            recipient=agent,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).values_list('created_at', flat=True)
        
        # Count messages by hour
        for timestamp in sent_messages:
            hour = timestamp.hour
            hour_buckets[hour] += 1
        
        for timestamp in received_messages:
            hour = timestamp.hour
            hour_buckets[hour] += 1
        
        return {
            'message_frequency_per_hour': hour_buckets
        }
    
    @staticmethod
    def _calculate_peak_hours(
        frequency_distribution: Dict[int, int]
    ) -> Dict[str, Any]:
        """
        Identify peak activity hours from frequency distribution.
        
        Requirement: 7.5
        """
        if not frequency_distribution:
            return {
                'peak_activity_hours': [],
                'peak_hour_message_count': 0
            }
        
        # Sort hours by message count (descending)
        sorted_hours = sorted(
            frequency_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Get top 3 hours
        peak_hours = [hour for hour, count in sorted_hours[:3] if count > 0]
        peak_count = sorted_hours[0][1] if sorted_hours else 0
        
        return {
            'peak_activity_hours': peak_hours,
            'peak_hour_message_count': peak_count
        }
    
    @staticmethod
    def _detect_patterns(
        agent: AIAgent,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Detect conversation patterns including style, consistency, and topics.
        
        Requirement: 7.6
        """
        # Get all messages
        sent_messages = list(AgentMessage.objects.filter(
            sender=agent,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).order_by('created_at'))
        
        received_messages = list(AgentMessage.objects.filter(
            recipient=agent,
            created_at__gte=start_time,
            created_at__lte=end_time
        ).order_by('created_at'))
        
        all_messages = sent_messages + received_messages
        
        if not all_messages:
            return {
                'conversation_style': 'unknown',
                'average_message_length': 0,
                'response_consistency': 0.0,
                'topic_keywords': []
            }
        
        # Calculate average message length
        total_length = sum(len(msg.content) for msg in all_messages)
        avg_length = total_length / len(all_messages)
        
        # Determine conversation style based on message length
        if avg_length < 100:
            style = 'brief'
        elif avg_length < 500:
            style = 'moderate'
        else:
            style = 'detailed'
        
        # Calculate response consistency
        response_times = []
        for received_msg in received_messages:
            response = AgentMessage.objects.filter(
                sender=agent,
                recipient=received_msg.sender,
                created_at__gt=received_msg.created_at,
                created_at__lte=received_msg.created_at + timedelta(minutes=60)
            ).order_by('created_at').first()
            
            if response:
                response_time = (response.created_at - received_msg.created_at).total_seconds()
                response_times.append(response_time)
        
        if len(response_times) > 1:
            # Calculate coefficient of variation (lower = more consistent)
            mean = sum(response_times) / len(response_times)
            variance = sum((x - mean) ** 2 for x in response_times) / len(response_times)
            std_dev = variance ** 0.5
            consistency = 1.0 - min(std_dev / mean if mean > 0 else 0, 1.0)
        else:
            consistency = 0.0
        
        # Extract topic keywords (simple word frequency analysis)
        all_content = ' '.join(msg.content for msg in all_messages)
        words = all_content.lower().split()
        
        # Filter out common words and get top keywords
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                       'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                       'i', 'you', 'he', 'she', 'it', 'we', 'they', 'this', 'that', 'these', 'those'}
        
        filtered_words = [w for w in words if len(w) > 3 and w not in common_words]
        word_counts = Counter(filtered_words)
        top_keywords = [word for word, count in word_counts.most_common(10)]
        
        return {
            'conversation_style': style,
            'average_message_length': avg_length,
            'response_consistency': consistency,
            'topic_keywords': top_keywords
        }

    
    @staticmethod
    def calculate_temporal_metrics(
        agent_id: str,
        time_range: Dict[str, datetime],
        aggregation_period: str = 'hourly'
    ) -> Dict[str, Any]:
        """
        Calculate metrics with temporal aggregation.
        
        Args:
            agent_id: UUID of the agent
            time_range: Dictionary with 'start_time' and 'end_time'
            aggregation_period: 'hourly', 'daily', or 'weekly'
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - aggregated_metrics: List of metrics grouped by time period
                - aggregation_period: The aggregation period used
                - error: Error message (on failure)
        
        Requirements: 19.1, 19.2, 19.3, 19.4
        """
        try:
            # Validate agent exists
            try:
                agent = AIAgent.objects.get(id=agent_id)
            except AIAgent.DoesNotExist:
                return {
                    'status': 'FAILED',
                    'error': 'Agent not found'
                }
            
            # Validate aggregation period
            valid_periods = ['hourly', 'daily', 'weekly']
            if aggregation_period not in valid_periods:
                return {
                    'status': 'FAILED',
                    'error': f'Invalid aggregation period. Must be one of: {", ".join(valid_periods)}'
                }
            
            start_time = time_range['start_time']
            end_time = time_range['end_time']
            
            # Generate time buckets based on aggregation period
            time_buckets = ResearchAnalyticsEngine._generate_time_buckets(
                start_time, end_time, aggregation_period
            )
            
            aggregated_metrics = []
            
            for bucket_start, bucket_end in time_buckets:
                # Calculate metrics for this time bucket
                bucket_metrics = ResearchAnalyticsEngine.calculate_metrics(
                    agent_id=str(agent.id),
                    time_range={'start_time': bucket_start, 'end_time': bucket_end}
                )
                
                if bucket_metrics['status'] == 'SUCCESS':
                    aggregated_metrics.append({
                        'period_start': bucket_start.isoformat(),
                        'period_end': bucket_end.isoformat(),
                        'metrics': bucket_metrics['metrics']
                    })
            
            return {
                'status': 'SUCCESS',
                'aggregated_metrics': aggregated_metrics,
                'aggregation_period': aggregation_period
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.analytics')
            logger.error(f'Failed to calculate temporal metrics: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def _generate_time_buckets(
        start_time: datetime,
        end_time: datetime,
        aggregation_period: str
    ) -> List[Tuple[datetime, datetime]]:
        """
        Generate time buckets for aggregation.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            aggregation_period: 'hourly', 'daily', or 'weekly'
        
        Returns:
            List of (bucket_start, bucket_end) tuples
        """
        buckets = []
        current = start_time
        
        if aggregation_period == 'hourly':
            delta = timedelta(hours=1)
        elif aggregation_period == 'daily':
            delta = timedelta(days=1)
        elif aggregation_period == 'weekly':
            delta = timedelta(weeks=1)
        else:
            delta = timedelta(hours=1)  # Default to hourly
        
        while current < end_time:
            bucket_end = min(current + delta, end_time)
            buckets.append((current, bucket_end))
            current = bucket_end
        
        return buckets
    
    @staticmethod
    def calculate_thread_metrics(
        thread_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        time_range: Optional[Dict[str, datetime]] = None
    ) -> Dict[str, Any]:
        """
        Calculate thread-level analytics for conversation threads.
        
        Args:
            thread_id: Optional specific thread ID (parent message ID)
            agent_id: Optional agent ID to filter threads
            time_range: Optional time range filter
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - threads: List of thread metrics
                - error: Error message (on failure)
        
        Requirements: 17.4, 17.5
        """
        try:
            # Build query for messages
            query = Q()
            
            if thread_id:
                # Get all messages in this thread
                query &= Q(parent_message_id=thread_id) | Q(id=thread_id)
            
            if agent_id:
                # Get threads involving this agent
                query &= Q(sender_id=agent_id) | Q(recipient_id=agent_id)
            
            if time_range:
                query &= Q(created_at__gte=time_range['start_time'])
                query &= Q(created_at__lte=time_range['end_time'])
            
            # Get messages
            messages = AgentMessage.objects.filter(query).order_by('created_at')
            
            # Group messages by thread (parent_message_id)
            threads = defaultdict(list)
            
            for msg in messages:
                # Use parent_message_id as thread identifier, or message id if it's a root message
                thread_key = str(msg.parent_message_id) if msg.parent_message_id else str(msg.id)
                threads[thread_key].append(msg)
            
            # Calculate metrics for each thread
            thread_metrics = []
            
            for thread_key, thread_messages in threads.items():
                if not thread_messages:
                    continue
                
                # Calculate thread-level metrics
                participants = set()
                for msg in thread_messages:
                    participants.add(str(msg.sender_id))
                    participants.add(str(msg.recipient_id))
                
                first_message = thread_messages[0]
                last_message = thread_messages[-1]
                duration_seconds = (last_message.created_at - first_message.created_at).total_seconds()
                
                # Calculate thread depth (max nesting level)
                thread_depth = ResearchAnalyticsEngine._calculate_thread_depth(thread_messages)
                
                thread_metrics.append({
                    'thread_id': thread_key,
                    'message_count': len(thread_messages),
                    'participant_count': len(participants),
                    'participants': list(participants),
                    'duration_seconds': duration_seconds,
                    'thread_depth': thread_depth,
                    'started_at': first_message.created_at.isoformat(),
                    'last_message_at': last_message.created_at.isoformat()
                })
            
            return {
                'status': 'SUCCESS',
                'threads': thread_metrics,
                'thread_count': len(thread_metrics)
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.analytics')
            logger.error(f'Failed to calculate thread metrics: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def _calculate_thread_depth(messages: List[AgentMessage]) -> int:
        """
        Calculate the maximum depth of a conversation thread.
        
        Args:
            messages: List of messages in the thread
        
        Returns:
            Maximum thread depth (nesting level)
        """
        if not messages:
            return 0
        
        # Build parent-child relationships
        message_map = {str(msg.id): msg for msg in messages}
        depth_map = {}
        
        def get_depth(msg_id: str) -> int:
            if msg_id in depth_map:
                return depth_map[msg_id]
            
            msg = message_map.get(msg_id)
            if not msg or not msg.parent_message_id:
                depth = 1
            else:
                parent_id = str(msg.parent_message_id)
                depth = get_depth(parent_id) + 1
            
            depth_map[msg_id] = depth
            return depth
        
        # Calculate depth for all messages
        max_depth = 0
        for msg in messages:
            depth = get_depth(str(msg.id))
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    @staticmethod
    def store_metrics(
        metrics: Dict[str, Any],
        agent_id: Optional[str] = None,
        interaction_id: Optional[str] = None,
        aggregation_period: Optional[str] = None,
        dimensions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store calculated metrics in the ResearchMetric table.
        
        Args:
            metrics: Dictionary of metric name -> value pairs
            agent_id: Optional agent ID to associate metrics with
            interaction_id: Optional interaction ID to associate metrics with
            aggregation_period: Optional aggregation period (hourly, daily, weekly)
            dimensions: Optional multi-dimensional metric dimensions
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - stored_count: Number of metrics stored
                - metric_ids: List of created metric IDs
                - error: Error message (on failure)
        
        Requirements: 7.7, 7.8, 19.5
        """
        try:
            # Validate agent if provided
            agent = None
            if agent_id:
                try:
                    agent = AIAgent.objects.get(id=agent_id)
                except AIAgent.DoesNotExist:
                    return {
                        'status': 'FAILED',
                        'error': 'Agent not found'
                    }
            
            # Validate interaction if provided
            interaction = None
            if interaction_id:
                try:
                    interaction = AgentInteraction.objects.get(id=interaction_id)
                except AgentInteraction.DoesNotExist:
                    return {
                        'status': 'FAILED',
                        'error': 'Interaction not found'
                    }
            
            metric_ids = []
            stored_count = 0
            
            # Store each metric
            for metric_name, metric_value in metrics.items():
                # Determine metric type based on value
                if isinstance(metric_value, (int, float)):
                    metric_type = 'GAUGE'
                    value = float(metric_value)
                elif isinstance(metric_value, list):
                    # Store list metrics as JSON in dimensions
                    metric_type = 'SUMMARY'
                    value = float(len(metric_value))
                    if dimensions is None:
                        dimensions = {}
                    dimensions[metric_name] = metric_value
                elif isinstance(metric_value, dict):
                    # Store dict metrics as JSON in dimensions
                    metric_type = 'SUMMARY'
                    value = float(len(metric_value))
                    if dimensions is None:
                        dimensions = {}
                    dimensions[metric_name] = metric_value
                else:
                    # Skip unsupported types
                    continue
                
                # Determine unit based on metric name
                unit = ResearchAnalyticsEngine._determine_unit(metric_name)
                
                # Create metric record
                metric = ResearchMetric.objects.create(
                    metric_name=metric_name,
                    metric_type=metric_type,
                    agent=agent,
                    interaction=interaction,
                    value=value,
                    unit=unit,
                    dimensions=dimensions or {},
                    aggregation_period=aggregation_period or ''
                )
                
                metric_ids.append(str(metric.id))
                stored_count += 1
            
            return {
                'status': 'SUCCESS',
                'stored_count': stored_count,
                'metric_ids': metric_ids
            }
            
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.analytics')
            logger.error(f'Failed to store metrics: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def _determine_unit(metric_name: str) -> str:
        """
        Determine the unit of measurement based on metric name.
        
        Args:
            metric_name: Name of the metric
        
        Returns:
            Unit string (e.g., 'count', 'ms', 'seconds')
        """
        if 'time' in metric_name.lower() and 'ms' in metric_name.lower():
            return 'milliseconds'
        elif 'time' in metric_name.lower():
            return 'seconds'
        elif 'count' in metric_name.lower() or 'total' in metric_name.lower():
            return 'count'
        elif 'percentage' in metric_name.lower() or 'ratio' in metric_name.lower():
            return 'percentage'
        elif 'length' in metric_name.lower():
            return 'characters'
        else:
            return 'count'
    
    @staticmethod
    def generate_report(
        report_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive analytics report.
        
        Args:
            report_type: Type of report ('agent_summary', 'interaction_analysis', 'temporal_trends')
            parameters: Report-specific parameters
        
        Returns:
            Dictionary containing:
                - status: 'SUCCESS' or 'FAILED'
                - report: Generated report data
                - report_type: Type of report generated
                - error: Error message (on failure)
        """
        try:
            if report_type == 'agent_summary':
                return ResearchAnalyticsEngine._generate_agent_summary_report(parameters)
            elif report_type == 'interaction_analysis':
                return ResearchAnalyticsEngine._generate_interaction_analysis_report(parameters)
            elif report_type == 'temporal_trends':
                return ResearchAnalyticsEngine._generate_temporal_trends_report(parameters)
            else:
                return {
                    'status': 'FAILED',
                    'error': f'Unknown report type: {report_type}'
                }
        
        except Exception as e:
            import logging
            logger = logging.getLogger('ai_agents.analytics')
            logger.error(f'Failed to generate report: {str(e)}')
            
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    @staticmethod
    def _generate_agent_summary_report(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate agent summary report."""
        agent_id = parameters.get('agent_id')
        time_range = parameters.get('time_range')
        
        if not agent_id or not time_range:
            return {
                'status': 'FAILED',
                'error': 'agent_id and time_range are required'
            }
        
        # Calculate all metrics
        metrics_result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=agent_id,
            time_range=time_range
        )
        
        if metrics_result['status'] != 'SUCCESS':
            return metrics_result
        
        # Calculate thread metrics
        thread_result = ResearchAnalyticsEngine.calculate_thread_metrics(
            agent_id=agent_id,
            time_range=time_range
        )
        
        report = {
            'agent_id': agent_id,
            'time_range': {
                'start': time_range['start_time'].isoformat(),
                'end': time_range['end_time'].isoformat()
            },
            'metrics': metrics_result['metrics'],
            'threads': thread_result.get('threads', []) if thread_result['status'] == 'SUCCESS' else []
        }
        
        return {
            'status': 'SUCCESS',
            'report': report,
            'report_type': 'agent_summary'
        }
    
    @staticmethod
    def _generate_interaction_analysis_report(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate interaction analysis report."""
        agent_ids = parameters.get('agent_ids', [])
        time_range = parameters.get('time_range')
        
        if not time_range:
            return {
                'status': 'FAILED',
                'error': 'time_range is required'
            }
        
        # Get interactions
        query = Q(
            started_at__gte=time_range['start_time'],
            started_at__lte=time_range['end_time']
        )
        
        if agent_ids:
            query &= Q(agent_1_id__in=agent_ids) | Q(agent_2_id__in=agent_ids)
        
        interactions = AgentInteraction.objects.filter(query)
        
        # Analyze interactions
        interaction_data = []
        for interaction in interactions:
            interaction_data.append({
                'id': str(interaction.id),
                'session_id': str(interaction.session_id),
                'agent_1': str(interaction.agent_1_id),
                'agent_2': str(interaction.agent_2_id),
                'type': interaction.interaction_type,
                'message_count': interaction.message_count,
                'duration_seconds': interaction.total_duration_seconds,
                'started_at': interaction.started_at.isoformat(),
                'ended_at': interaction.ended_at.isoformat() if interaction.ended_at else None
            })
        
        report = {
            'time_range': {
                'start': time_range['start_time'].isoformat(),
                'end': time_range['end_time'].isoformat()
            },
            'total_interactions': len(interaction_data),
            'interactions': interaction_data
        }
        
        return {
            'status': 'SUCCESS',
            'report': report,
            'report_type': 'interaction_analysis'
        }
    
    @staticmethod
    def _generate_temporal_trends_report(parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate temporal trends report."""
        agent_id = parameters.get('agent_id')
        time_range = parameters.get('time_range')
        aggregation_period = parameters.get('aggregation_period', 'daily')
        
        if not agent_id or not time_range:
            return {
                'status': 'FAILED',
                'error': 'agent_id and time_range are required'
            }
        
        # Calculate temporal metrics
        temporal_result = ResearchAnalyticsEngine.calculate_temporal_metrics(
            agent_id=agent_id,
            time_range=time_range,
            aggregation_period=aggregation_period
        )
        
        if temporal_result['status'] != 'SUCCESS':
            return temporal_result
        
        report = {
            'agent_id': agent_id,
            'time_range': {
                'start': time_range['start_time'].isoformat(),
                'end': time_range['end_time'].isoformat()
            },
            'aggregation_period': aggregation_period,
            'temporal_metrics': temporal_result['aggregated_metrics']
        }
        
        return {
            'status': 'SUCCESS',
            'report': report,
            'report_type': 'temporal_trends'
        }
