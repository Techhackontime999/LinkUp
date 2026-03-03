"""
Unit tests for the Research Analytics Engine.

Tests cover:
- Basic metric calculations (message counts, conversation partners, response time)
- Temporal analytics (hourly, daily, weekly aggregation)
- Pattern detection (conversation style, response consistency)
- Thread-level analytics
- Metric storage
"""
import uuid
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from .models import AIAgent, AgentMessage, AgentInteraction, ResearchMetric
from .analytics_engine import ResearchAnalyticsEngine


class ResearchAnalyticsEngineTestCase(TestCase):
    """Test cases for ResearchAnalyticsEngine service."""
    
    def setUp(self):
        """Set up test data."""
        # Create test agents
        self.agent1 = AIAgent.objects.create(
            name='TestAgent1',
            agent_type='CONVERSATIONAL',
            description='Test agent 1',
            capabilities={'test': True},
            owner_email='test1@example.com',
            api_key_hash='hash1',
            is_active=True
        )
        
        self.agent2 = AIAgent.objects.create(
            name='TestAgent2',
            agent_type='CONVERSATIONAL',
            description='Test agent 2',
            capabilities={'test': True},
            owner_email='test2@example.com',
            api_key_hash='hash2',
            is_active=True
        )
        
        self.agent3 = AIAgent.objects.create(
            name='TestAgent3',
            agent_type='TASK_BASED',
            description='Test agent 3',
            capabilities={'test': True},
            owner_email='test3@example.com',
            api_key_hash='hash3',
            is_active=True
        )
        
        # Create test messages
        self.base_time = timezone.now() - timedelta(days=1)
        self._create_test_messages()
    
    def _create_test_messages(self):
        """Create test messages for analytics."""
        # Agent1 sends 5 messages to Agent2
        for i in range(5):
            AgentMessage.objects.create(
                sender=self.agent1,
                recipient=self.agent2,
                content=f'Test message {i} from agent1 to agent2',
                status='DELIVERED',
                created_at=self.base_time + timedelta(hours=i)
            )
        
        # Agent2 sends 3 messages to Agent1 (responses)
        for i in range(3):
            AgentMessage.objects.create(
                sender=self.agent2,
                recipient=self.agent1,
                content=f'Response {i} from agent2 to agent1',
                status='DELIVERED',
                created_at=self.base_time + timedelta(hours=i, minutes=10)
            )
        
        # Agent1 sends 2 messages to Agent3
        for i in range(2):
            AgentMessage.objects.create(
                sender=self.agent1,
                recipient=self.agent3,
                content=f'Test message {i} from agent1 to agent3',
                status='DELIVERED',
                created_at=self.base_time + timedelta(hours=i + 6)
            )
    
    def test_calculate_message_counts(self):
        """Test basic message count calculations."""
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            metric_types=['message_counts']
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        metrics = result['metrics']
        
        # Agent1 sent 7 messages (5 to agent2, 2 to agent3)
        self.assertEqual(metrics['total_messages_sent'], 7)
        
        # Agent1 received 3 messages (from agent2)
        self.assertEqual(metrics['total_messages_received'], 3)
        
        # Total messages
        self.assertEqual(metrics['total_messages'], 10)
    
    def test_calculate_conversation_partners(self):
        """Test unique conversation partner identification."""
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            metric_types=['conversation_partners']
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        metrics = result['metrics']
        
        # Agent1 communicated with Agent2 and Agent3
        self.assertEqual(metrics['unique_conversation_partners'], 2)
        
        # Check partner IDs
        partner_ids = set(metrics['conversation_partner_ids'])
        self.assertIn(str(self.agent2.id), partner_ids)
        self.assertIn(str(self.agent3.id), partner_ids)
    
    def test_calculate_response_time(self):
        """Test average response time calculation."""
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            metric_types=['response_time']
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        metrics = result['metrics']
        
        # Agent1 received 3 messages and should have responded to them
        # Response time should be around 10 minutes (600,000 ms)
        self.assertGreater(metrics['average_response_time_ms'], 0)
        self.assertEqual(metrics['response_count'], 3)
    
    def test_calculate_frequency_distribution(self):
        """Test message frequency distribution by hour."""
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            metric_types=['frequency_distribution']
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        metrics = result['metrics']
        
        # Check that frequency distribution has 24 hours
        freq_dist = metrics['message_frequency_per_hour']
        self.assertEqual(len(freq_dist), 24)
        
        # Check that some hours have messages
        total_messages = sum(freq_dist.values())
        self.assertGreater(total_messages, 0)
    
    def test_calculate_peak_hours(self):
        """Test peak activity hour identification."""
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            metric_types=['frequency_distribution', 'peak_hours']
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        metrics = result['metrics']
        
        # Check peak hours
        peak_hours = metrics['peak_activity_hours']
        self.assertIsInstance(peak_hours, list)
        self.assertLessEqual(len(peak_hours), 3)
        
        # Peak hour message count should be positive
        self.assertGreaterEqual(metrics['peak_hour_message_count'], 0)
    
    def test_detect_patterns(self):
        """Test conversation pattern detection."""
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            metric_types=['patterns']
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        metrics = result['metrics']
        
        # Check pattern metrics
        self.assertIn('conversation_style', metrics)
        self.assertIn(metrics['conversation_style'], ['brief', 'moderate', 'detailed'])
        
        self.assertIn('average_message_length', metrics)
        self.assertGreater(metrics['average_message_length'], 0)
        
        self.assertIn('response_consistency', metrics)
        self.assertGreaterEqual(metrics['response_consistency'], 0.0)
        self.assertLessEqual(metrics['response_consistency'], 1.0)
        
        self.assertIn('topic_keywords', metrics)
        self.assertIsInstance(metrics['topic_keywords'], list)
    
    def test_calculate_temporal_metrics_hourly(self):
        """Test hourly temporal aggregation."""
        time_range = {
            'start_time': self.base_time,
            'end_time': self.base_time + timedelta(hours=3)
        }
        
        result = ResearchAnalyticsEngine.calculate_temporal_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            aggregation_period='hourly'
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['aggregation_period'], 'hourly')
        
        # Should have 3 hourly buckets
        aggregated = result['aggregated_metrics']
        self.assertEqual(len(aggregated), 3)
        
        # Each bucket should have metrics
        for bucket in aggregated:
            self.assertIn('period_start', bucket)
            self.assertIn('period_end', bucket)
            self.assertIn('metrics', bucket)
    
    def test_calculate_temporal_metrics_daily(self):
        """Test daily temporal aggregation."""
        time_range = {
            'start_time': self.base_time,
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.calculate_temporal_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            aggregation_period='daily'
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['aggregation_period'], 'daily')
        
        # Should have 2 daily buckets
        aggregated = result['aggregated_metrics']
        self.assertEqual(len(aggregated), 2)
    
    def test_calculate_thread_metrics(self):
        """Test thread-level analytics."""
        # Create a threaded conversation
        parent_msg = AgentMessage.objects.create(
            sender=self.agent1,
            recipient=self.agent2,
            content='Parent message',
            status='DELIVERED',
            created_at=timezone.now()
        )
        
        # Create replies
        for i in range(3):
            AgentMessage.objects.create(
                sender=self.agent2,
                recipient=self.agent1,
                content=f'Reply {i}',
                status='DELIVERED',
                parent_message=parent_msg,
                created_at=timezone.now() + timedelta(minutes=i+1)
            )
        
        result = ResearchAnalyticsEngine.calculate_thread_metrics(
            thread_id=str(parent_msg.id)
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        threads = result['threads']
        
        # Should have at least one thread
        self.assertGreater(len(threads), 0)
        
        # Check thread metrics
        thread = threads[0]
        self.assertIn('thread_id', thread)
        self.assertIn('message_count', thread)
        self.assertIn('participant_count', thread)
        self.assertIn('duration_seconds', thread)
        self.assertIn('thread_depth', thread)
    
    def test_store_metrics(self):
        """Test metric storage in ResearchMetric table."""
        metrics = {
            'total_messages': 10,
            'average_response_time_ms': 5000.0,
            'unique_partners': 2
        }
        
        result = ResearchAnalyticsEngine.store_metrics(
            metrics=metrics,
            agent_id=str(self.agent1.id),
            aggregation_period='daily'
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['stored_count'], 3)
        self.assertEqual(len(result['metric_ids']), 3)
        
        # Verify metrics were stored
        stored_metrics = ResearchMetric.objects.filter(agent=self.agent1)
        self.assertEqual(stored_metrics.count(), 3)
        
        # Check metric details
        for metric in stored_metrics:
            self.assertEqual(metric.aggregation_period, 'daily')
            self.assertIn(metric.metric_name, metrics.keys())
    
    def test_store_metrics_with_dimensions(self):
        """Test storing multi-dimensional metrics."""
        metrics = {
            'message_frequency': {'hour_0': 5, 'hour_1': 3, 'hour_2': 7}
        }
        
        dimensions = {
            'time_zone': 'UTC',
            'agent_type': 'CONVERSATIONAL'
        }
        
        result = ResearchAnalyticsEngine.store_metrics(
            metrics=metrics,
            agent_id=str(self.agent1.id),
            dimensions=dimensions
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        
        # Verify dimensions were stored
        stored_metric = ResearchMetric.objects.filter(
            agent=self.agent1,
            metric_name='message_frequency'
        ).first()
        
        self.assertIsNotNone(stored_metric)
        self.assertIn('time_zone', stored_metric.dimensions)
        self.assertIn('agent_type', stored_metric.dimensions)
    
    def test_generate_agent_summary_report(self):
        """Test agent summary report generation."""
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.generate_report(
            report_type='agent_summary',
            parameters={
                'agent_id': str(self.agent1.id),
                'time_range': time_range
            }
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['report_type'], 'agent_summary')
        
        report = result['report']
        self.assertIn('agent_id', report)
        self.assertIn('time_range', report)
        self.assertIn('metrics', report)
        self.assertIn('threads', report)
    
    def test_generate_interaction_analysis_report(self):
        """Test interaction analysis report generation."""
        # Create an interaction
        AgentInteraction.objects.create(
            agent_1=self.agent1,
            agent_2=self.agent2,
            interaction_type='CONVERSATION',
            started_at=self.base_time,
            message_count=5
        )
        
        time_range = {
            'start_time': self.base_time - timedelta(hours=1),
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.generate_report(
            report_type='interaction_analysis',
            parameters={
                'time_range': time_range
            }
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['report_type'], 'interaction_analysis')
        
        report = result['report']
        self.assertIn('total_interactions', report)
        self.assertIn('interactions', report)
        self.assertGreater(report['total_interactions'], 0)
    
    def test_generate_temporal_trends_report(self):
        """Test temporal trends report generation."""
        time_range = {
            'start_time': self.base_time,
            'end_time': self.base_time + timedelta(days=2)
        }
        
        result = ResearchAnalyticsEngine.generate_report(
            report_type='temporal_trends',
            parameters={
                'agent_id': str(self.agent1.id),
                'time_range': time_range,
                'aggregation_period': 'daily'
            }
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['report_type'], 'temporal_trends')
        
        report = result['report']
        self.assertIn('agent_id', report)
        self.assertIn('aggregation_period', report)
        self.assertIn('temporal_metrics', report)
    
    def test_invalid_agent_id(self):
        """Test error handling for invalid agent ID."""
        time_range = {
            'start_time': self.base_time,
            'end_time': self.base_time + timedelta(days=1)
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(uuid.uuid4()),  # Non-existent agent
            time_range=time_range
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('error', result)
    
    def test_invalid_time_range(self):
        """Test error handling for invalid time range."""
        time_range = {
            'start_time': self.base_time + timedelta(days=1),
            'end_time': self.base_time  # End before start
        }
        
        result = ResearchAnalyticsEngine.calculate_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('error', result)
    
    def test_invalid_aggregation_period(self):
        """Test error handling for invalid aggregation period."""
        time_range = {
            'start_time': self.base_time,
            'end_time': self.base_time + timedelta(days=1)
        }
        
        result = ResearchAnalyticsEngine.calculate_temporal_metrics(
            agent_id=str(self.agent1.id),
            time_range=time_range,
            aggregation_period='invalid'
        )
        
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('error', result)
