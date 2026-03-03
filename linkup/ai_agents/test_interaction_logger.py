"""
Tests for InteractionLogger service.
"""
from django.test import TestCase
from django.utils import timezone
from .models import AIAgent, AgentMessage, AgentInteraction, ResearchMetric
from .services import InteractionLogger


class InteractionLoggerTests(TestCase):
    """Test cases for InteractionLogger service."""
    
    def setUp(self):
        """Set up test data."""
        # Create test agents
        self.agent1 = AIAgent.objects.create(
            name='TestAgent1',
            agent_type='CONVERSATIONAL',
            description='Test agent 1',
            capabilities={'test': True},
            owner_email='test1@example.com',
            api_key_hash='test_hash_1'
        )
        
        self.agent2 = AIAgent.objects.create(
            name='TestAgent2',
            agent_type='TASK_BASED',
            description='Test agent 2',
            capabilities={'test': True},
            owner_email='test2@example.com',
            api_key_hash='test_hash_2'
        )
        
        # Create test message
        self.message = AgentMessage.objects.create(
            sender=self.agent1,
            recipient=self.agent2,
            content='Test message',
            message_type='TEXT',
            status='PENDING'
        )
    
    def tearDown(self):
        """Clean up test data."""
        AgentMessage.objects.all().delete()
        AgentInteraction.objects.all().delete()
        ResearchMetric.objects.all().delete()
        AIAgent.objects.all().delete()
    
    def test_log_interaction_creates_new_interaction(self):
        """Test that log_interaction creates a new interaction."""
        result = InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now(),
            interaction_type='CONVERSATION'
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('interaction_id', result)
        self.assertIn('session_id', result)
        
        # Verify interaction was created
        interaction = AgentInteraction.objects.get(id=result['interaction_id'])
        self.assertEqual(interaction.agent_1, self.agent1)
        self.assertEqual(interaction.agent_2, self.agent2)
        self.assertEqual(interaction.message_count, 1)
        self.assertEqual(interaction.interaction_type, 'CONVERSATION')
    
    def test_log_interaction_with_tags_and_metrics(self):
        """Test that log_interaction stores tags and custom metrics."""
        tags = ['test', 'experiment']
        custom_metrics = {'test_metric': 42}
        
        result = InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now(),
            tags=tags,
            custom_metrics=custom_metrics
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        
        # Verify tags and metrics were stored
        interaction = AgentInteraction.objects.get(id=result['interaction_id'])
        self.assertEqual(interaction.tags, tags)
        self.assertIn('test_metric', interaction.metrics)
        self.assertEqual(interaction.metrics['test_metric'], 42)
    
    def test_log_interaction_updates_existing_session(self):
        """Test that log_interaction updates existing active session."""
        # Create first interaction
        result1 = InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now()
        )
        
        interaction_id1 = result1['interaction_id']
        
        # Create second message
        message2 = AgentMessage.objects.create(
            sender=self.agent1,
            recipient=self.agent2,
            content='Second message',
            message_type='TEXT',
            status='PENDING'
        )
        
        # Log second interaction (should update existing)
        result2 = InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=message2,
            timestamp=timezone.now()
        )
        
        # Should return same interaction ID
        self.assertEqual(result2['interaction_id'], interaction_id1)
        
        # Verify message count was incremented
        interaction = AgentInteraction.objects.get(id=interaction_id1)
        self.assertEqual(interaction.message_count, 2)
    
    def test_log_agent_action(self):
        """Test that log_agent_action creates a metric record."""
        result = InteractionLogger.log_agent_action(
            agent_id=str(self.agent1.id),
            action_type='message_sent',
            details={'recipient': str(self.agent2.id)}
        )
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn('metric_id', result)
        
        # Verify metric was created
        metric = ResearchMetric.objects.get(id=result['metric_id'])
        self.assertEqual(metric.agent, self.agent1)
        self.assertEqual(metric.metric_type, 'COUNTER')
        self.assertEqual(metric.value, 1.0)
        self.assertIn('action_type', metric.dimensions)
    
    def test_end_interaction_session(self):
        """Test that end_interaction_session calculates duration and message count."""
        # Create interaction
        result = InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now()
        )
        
        interaction_id = result['interaction_id']
        
        # End the session
        end_result = InteractionLogger.end_interaction_session(interaction_id)
        
        self.assertEqual(end_result['status'], 'SUCCESS')
        self.assertIn('total_duration_seconds', end_result)
        self.assertIn('message_count', end_result)
        self.assertEqual(end_result['message_count'], 1)
        
        # Verify interaction was updated
        interaction = AgentInteraction.objects.get(id=interaction_id)
        self.assertIsNotNone(interaction.ended_at)
        self.assertGreaterEqual(interaction.total_duration_seconds, 0)
    
    def test_query_interactions(self):
        """Test that query_interactions filters and returns interactions."""
        # Create multiple interactions
        InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now(),
            interaction_type='CONVERSATION',
            tags=['test1']
        )
        
        message2 = AgentMessage.objects.create(
            sender=self.agent2,
            recipient=self.agent1,
            content='Reply message',
            message_type='TEXT',
            status='PENDING'
        )
        
        InteractionLogger.log_interaction(
            agent_1=self.agent2,
            agent_2=self.agent1,
            message=message2,
            timestamp=timezone.now(),
            interaction_type='COLLABORATION',
            tags=['test2']
        )
        
        # Query all interactions
        result = InteractionLogger.query_interactions()
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['count'], 2)
        
        # Query with filter
        result_filtered = InteractionLogger.query_interactions(
            filters={'interaction_type': 'CONVERSATION'}
        )
        self.assertEqual(result_filtered['status'], 'SUCCESS')
        self.assertEqual(result_filtered['count'], 1)
    
    def test_export_interaction_data_json(self):
        """Test that export_interaction_data exports to JSON format."""
        # Create interaction
        InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now()
        )
        
        # Export to JSON
        result = InteractionLogger.export_interaction_data(format='json')
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['format'], 'json')
        self.assertEqual(result['count'], 1)
        self.assertIn('data', result)
        
        # Verify JSON is valid
        import json
        data = json.loads(result['data'])
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
    
    def test_export_interaction_data_csv(self):
        """Test that export_interaction_data exports to CSV format."""
        # Create interaction
        InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now()
        )
        
        # Export to CSV
        result = InteractionLogger.export_interaction_data(format='csv')
        
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertEqual(result['format'], 'csv')
        self.assertEqual(result['count'], 1)
        self.assertIn('data', result)
        
        # Verify CSV has header
        self.assertIn('id,session_id', result['data'])
    
    def test_anonymize_data(self):
        """Test that anonymize_data replaces agent IDs with pseudonyms."""
        # Create interaction
        result = InteractionLogger.log_interaction(
            agent_1=self.agent1,
            agent_2=self.agent2,
            message=self.message,
            timestamp=timezone.now()
        )
        
        interaction_id = result['interaction_id']
        
        # Anonymize the interaction
        anon_result = InteractionLogger.anonymize_data([interaction_id])
        
        self.assertEqual(anon_result['status'], 'SUCCESS')
        self.assertEqual(anon_result['anonymized_count'], 1)
        self.assertIn('pseudonym_map', anon_result)
        
        # Verify pseudonyms were created
        self.assertIn(str(self.agent1.id), anon_result['pseudonym_map'])
        self.assertIn(str(self.agent2.id), anon_result['pseudonym_map'])
        
        # Verify interaction was marked as archived
        interaction = AgentInteraction.objects.get(id=interaction_id)
        self.assertTrue(interaction.is_archived)
        self.assertTrue(interaction.metrics.get('anonymized', False))
