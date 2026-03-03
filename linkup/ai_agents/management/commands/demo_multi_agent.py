"""
Django management command to demonstrate multi-agent interactions.
Usage: python manage.py demo_multi_agent
"""
from django.core.management.base import BaseCommand
from ai_agents.agent_integrations import demo_multi_agent_interaction


class Command(BaseCommand):
    help = 'Demonstrate multi-agent AI interactions on the platform'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Multi-Agent Demo...\n'))
        
        try:
            orchestrator = demo_multi_agent_interaction()
            
            self.stdout.write(self.style.SUCCESS('\n✓ Demo completed successfully!'))
            self.stdout.write(self.style.SUCCESS(f'✓ {len(orchestrator.agents)} agents registered and interacting'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n✗ Demo failed: {str(e)}'))
