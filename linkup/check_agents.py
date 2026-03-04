"""
Quick diagnostic script to check AI agents in the database.
Run with: python manage.py shell < check_agents.py
"""
from ai_agents.models import AIAgent

print("\n=== AI Agent Diagnostic ===\n")

# Check total agents
total = AIAgent.objects.count()
print(f"Total agents in database: {total}")

# Check active agents
active = AIAgent.objects.filter(is_active=True).count()
print(f"Active agents: {active}")

# Check suspended agents
suspended = AIAgent.objects.filter(is_suspended=True).count()
print(f"Suspended agents: {suspended}")

# Check inactive agents
inactive = AIAgent.objects.filter(is_active=False).count()
print(f"Inactive agents: {inactive}")

# List all agents
print("\n=== All Agents ===")
for agent in AIAgent.objects.all():
    print(f"- {agent.name} (ID: {agent.id})")
    print(f"  Type: {agent.agent_type}")
    print(f"  Active: {agent.is_active}, Suspended: {agent.is_suspended}")
    print(f"  Owner: {agent.owner_email}")
    print(f"  Metadata: {agent.metadata}")
    print()

# Check if there are agents that should show but don't
should_show = AIAgent.objects.filter(is_active=True, is_suspended=False)
print(f"\n=== Agents that SHOULD show in admin panel ===")
print(f"Count: {should_show.count()}")
for agent in should_show:
    print(f"- {agent.name} (ID: {agent.id})")
