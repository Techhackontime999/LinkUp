"""
Simple test script to verify AgentCommunicationService implementation.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'linkup.settings')
django.setup()

from ai_agents.services import AgentRegistryService, AgentCommunicationService
from ai_agents.models import AIAgent, AgentMessage


def test_agent_communication():
    """Test the AgentCommunicationService implementation."""
    
    print("=" * 60)
    print("Testing AgentCommunicationService Implementation")
    print("=" * 60)
    
    # Clean up any existing test agents
    AIAgent.objects.filter(name__startswith='CommTestAgent').delete()
    
    # Step 1: Register two test agents
    print("\n1. Registering test agents...")
    
    agent1_result = AgentRegistryService.register_agent(
        name='CommTestAgent1',
        description='First test agent for communication',
        capabilities={'messaging': True},
        owner_email='agent1@test.com',
        agent_type='CONVERSATIONAL'
    )
    
    if agent1_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to register agent 1: {agent1_result.get('error')}")
        return False
    
    agent1_id = agent1_result['agent_id']
    print(f"   ✓ Agent 1 registered: {agent1_id}")
    
    agent2_result = AgentRegistryService.register_agent(
        name='CommTestAgent2',
        description='Second test agent for communication',
        capabilities={'messaging': True},
        owner_email='agent2@test.com',
        agent_type='CONVERSATIONAL'
    )
    
    if agent2_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to register agent 2: {agent2_result.get('error')}")
        return False
    
    agent2_id = agent2_result['agent_id']
    print(f"   ✓ Agent 2 registered: {agent2_id}")
    
    # Step 2: Test sending a message
    print("\n2. Testing message sending...")
    
    message_result = AgentCommunicationService.send_message(
        sender_id=agent1_id,
        recipient_id=agent2_id,
        content='Hello Agent 2! This is a test message.',
        metadata={'test': True, 'priority': 'high'}
    )
    
    if message_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to send message: {message_result.get('error')}")
        return False
    
    message_id = message_result['message_id']
    print(f"   ✓ Message sent successfully: {message_id}")
    print(f"   ✓ Delivery status: {message_result['delivery_status']}")
    
    # Step 3: Test message retrieval
    print("\n3. Testing message retrieval...")
    
    messages_result = AgentCommunicationService.receive_messages(
        agent_id=agent2_id
    )
    
    if messages_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to retrieve messages: {messages_result.get('error')}")
        return False
    
    print(f"   ✓ Retrieved {messages_result['count']} message(s)")
    
    if messages_result['count'] > 0:
        msg = messages_result['messages'][0]
        print(f"   ✓ Message content: {msg['content'][:50]}...")
        print(f"   ✓ Sender: {msg['sender_name']}")
    
    # Step 4: Test conversation history
    print("\n4. Testing conversation history...")
    
    # Send a reply
    reply_result = AgentCommunicationService.send_message(
        sender_id=agent2_id,
        recipient_id=agent1_id,
        content='Hello Agent 1! I received your message.',
        parent_message_id=message_id
    )
    
    if reply_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to send reply: {reply_result.get('error')}")
        return False
    
    print(f"   ✓ Reply sent successfully")
    
    # Get conversation history
    history_result = AgentCommunicationService.get_conversation_history(
        agent_id_1=agent1_id,
        agent_id_2=agent2_id
    )
    
    if history_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to get conversation history: {history_result.get('error')}")
        return False
    
    print(f"   ✓ Conversation history retrieved: {history_result['count']} message(s)")
    
    # Step 5: Test conversation threading
    print("\n5. Testing conversation threading...")
    
    thread_result = AgentCommunicationService.get_conversation_thread(
        message_id=message_id
    )
    
    if thread_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to get conversation thread: {thread_result.get('error')}")
        return False
    
    print(f"   ✓ Thread retrieved: {thread_result['message_count']} message(s)")
    print(f"   ✓ Thread depth: {thread_result['thread_depth']}")
    
    # Step 6: Test marking message as read
    print("\n6. Testing mark message as read...")
    
    read_result = AgentCommunicationService.mark_message_as_read(
        message_id=message_id,
        agent_id=agent2_id
    )
    
    if read_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to mark message as read: {read_result.get('error')}")
        return False
    
    print(f"   ✓ Message marked as read")
    
    # Step 7: Test broadcast message
    print("\n7. Testing broadcast message...")
    
    broadcast_result = AgentCommunicationService.broadcast_message(
        sender_id=agent1_id,
        recipient_ids=[agent2_id],
        content='This is a broadcast message',
        metadata={'broadcast': True}
    )
    
    if broadcast_result['status'] != 'SUCCESS':
        print(f"   ❌ Failed to broadcast message: {broadcast_result.get('error')}")
        return False
    
    print(f"   ✓ Broadcast sent: {broadcast_result['successful']} successful, {broadcast_result['failed']} failed")
    
    # Step 8: Test validation
    print("\n8. Testing message validation...")
    
    # Test sending to self (should fail)
    self_send_result = AgentCommunicationService.send_message(
        sender_id=agent1_id,
        recipient_id=agent1_id,
        content='Sending to myself'
    )
    
    if self_send_result['status'] == 'FAILED':
        print(f"   ✓ Correctly rejected self-send: {self_send_result.get('error')}")
    else:
        print(f"   ❌ Should have rejected self-send")
        return False
    
    # Test sending too large message (should fail)
    large_content = 'x' * 200000  # 200KB
    large_msg_result = AgentCommunicationService.send_message(
        sender_id=agent1_id,
        recipient_id=agent2_id,
        content=large_content
    )
    
    if large_msg_result['status'] == 'FAILED':
        print(f"   ✓ Correctly rejected oversized message: {large_msg_result.get('error')}")
    else:
        print(f"   ❌ Should have rejected oversized message")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All AgentCommunicationService tests passed!")
    print("=" * 60)
    
    # Clean up
    print("\nCleaning up test data...")
    AIAgent.objects.filter(name__startswith='CommTestAgent').delete()
    print("✓ Cleanup complete")
    
    return True


if __name__ == '__main__':
    try:
        success = test_agent_communication()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
