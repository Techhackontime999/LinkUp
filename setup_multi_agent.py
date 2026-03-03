#!/usr/bin/env python
"""
Setup script for Multi-Agent AI Platform.
This script helps you configure API keys for different AI agents.
"""
import os
import sys

def main():
    print("="*60)
    print("Multi-Agent AI Platform Setup")
    print("="*60)
    print()
    print("This script will help you configure API keys for AI agents.")
    print("You can get API keys from:")
    print("  - OpenAI (ChatGPT): https://platform.openai.com/api-keys")
    print("  - Google (Gemini): https://makersuite.google.com/app/apikey")
    print("  - Anthropic (Claude): https://console.anthropic.com/")
    print()
    print("Note: You can skip any agent by pressing Enter without typing a key.")
    print()
    
    # Get API keys
    openai_key = input("Enter your OpenAI API key (or press Enter to skip): ").strip()
    google_key = input("Enter your Google API key (or press Enter to skip): ").strip()
    anthropic_key = input("Enter your Anthropic API key (or press Enter to skip): ").strip()
    
    # Create or update .env file
    env_file = os.path.join('linkup', '.env')
    
    env_content = []
    
    if openai_key:
        env_content.append(f"OPENAI_API_KEY={openai_key}")
    
    if google_key:
        env_content.append(f"GOOGLE_API_KEY={google_key}")
    
    if anthropic_key:
        env_content.append(f"ANTHROPIC_API_KEY={anthropic_key}")
    
    if env_content:
        with open(env_file, 'a') as f:
            f.write('\n# AI Agent API Keys\n')
            f.write('\n'.join(env_content))
            f.write('\n')
        
        print()
        print("✓ API keys saved to linkup/.env")
        print()
        print("Next steps:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Start server: daphne -p 8000 professional_network.asgi:application")
        print("3. Visit: http://127.0.0.1:8000/ai-agents/multi-agent/chat/")
        print()
        print("Or run the demo: python manage.py demo_multi_agent")
    else:
        print()
        print("No API keys provided. You can still use the platform with mock responses.")
        print()
        print("To test the platform:")
        print("1. Run: python manage.py demo_multi_agent")
        print("2. Visit: http://127.0.0.1:8000/ai-agents/multi-agent/chat/")

if __name__ == '__main__':
    main()
