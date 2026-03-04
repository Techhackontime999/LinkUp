"""
Integration between AI Models and Social Platform

This module connects AI models (from AI Model Management) with the social platform,
allowing AI models to:
- Create posts on the social feed
- Respond to comments
- Interact with real users
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import AIAgent
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class AIModelSocialIntegration:
    """
    Service to integrate AI models with the social platform.
    """
    
    @staticmethod
    def create_user_for_ai_model(ai_model: AIAgent, password: str = None) -> User:
        """
        Create a Django User account for an AI model.
        
        This allows the AI model to:
        - Post on the social feed
        - Comment on posts
        - Appear as a regular user
        
        Args:
            ai_model: AIAgent instance
            password: Optional password (auto-generated if not provided)
        
        Returns:
            User instance linked to the AI model
        """
        try:
            with transaction.atomic():
                # Check if user already exists
                username = f"ai_{ai_model.name.lower().replace(' ', '_')}"
                
                if User.objects.filter(username=username).exists():
                    logger.warning(f"User {username} already exists")
                    return User.objects.get(username=username)
                
                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=ai_model.owner_email,
                    password=password or User.objects.make_random_password(),
                    first_name=ai_model.name,
                    is_active=ai_model.is_active
                )
                
                # Mark as AI user (you'll need to add this field to User model)
                # user.is_ai = True
                # user.ai_model_id = ai_model.id
                # user.save()
                
                logger.info(f"Created user {username} for AI model {ai_model.id}")
                return user
                
        except Exception as e:
            logger.error(f"Error creating user for AI model: {str(e)}")
            raise
    
    @staticmethod
    def create_post_as_ai(ai_model: AIAgent, content: str, image=None):
        """
        Create a post on the social feed as an AI model.
        
        Args:
            ai_model: AIAgent instance
            content: Post content
            image: Optional image file
        
        Returns:
            Post instance or None if failed
        """
        try:
            # Get or create user for AI model
            username = f"ai_{ai_model.name.lower().replace(' ', '_')}"
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = AIModelSocialIntegration.create_user_for_ai_model(ai_model)
            
            # Import Post model (adjust import based on your app structure)
            from feed.models import Post
            
            # Create post
            post = Post.objects.create(
                author=user,
                content=content,
                image=image
            )
            
            logger.info(f"AI model {ai_model.name} created post {post.id}")
            return post
            
        except Exception as e:
            logger.error(f"Error creating post for AI model: {str(e)}")
            return None
    
    @staticmethod
    def respond_to_comment(ai_model: AIAgent, comment, response_text: str):
        """
        AI model responds to a comment.
        
        Args:
            ai_model: AIAgent instance
            comment: Comment instance
            response_text: AI's response text
        
        Returns:
            Comment instance or None if failed
        """
        try:
            # Get user for AI model
            username = f"ai_{ai_model.name.lower().replace(' ', '_')}"
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = AIModelSocialIntegration.create_user_for_ai_model(ai_model)
            
            # Import Comment model (adjust based on your app structure)
            from feed.models import Comment
            
            # Create response comment
            response = Comment.objects.create(
                post=comment.post,
                author=user,
                content=response_text,
                parent=comment  # Reply to the original comment
            )
            
            logger.info(f"AI model {ai_model.name} responded to comment {comment.id}")
            return response
            
        except Exception as e:
            logger.error(f"Error creating response for AI model: {str(e)}")
            return None
    
    @staticmethod
    def generate_ai_response(ai_model: AIAgent, prompt: str) -> str:
        """
        Generate AI response based on the model's capabilities.
        
        This is a placeholder - you would integrate with actual AI services
        like OpenAI, Anthropic, or your own models.
        
        Args:
            ai_model: AIAgent instance
            prompt: User's message/comment
        
        Returns:
            AI-generated response text
        """
        # TODO: Integrate with actual AI service
        # For now, return a simple response
        
        capabilities = ai_model.capabilities or {}
        
        if capabilities.get('natural_language'):
            return f"Hello! I'm {ai_model.name}. I received your message: '{prompt}'. How can I help you?"
        else:
            return f"I'm {ai_model.name}, an AI assistant. I'm here to help!"
    
    @staticmethod
    def should_ai_respond(ai_model: AIAgent, content: str) -> bool:
        """
        Determine if AI model should respond to content.
        
        Args:
            ai_model: AIAgent instance
            content: Content to analyze
        
        Returns:
            True if AI should respond, False otherwise
        """
        # Check if AI is mentioned
        ai_username = f"ai_{ai_model.name.lower().replace(' ', '_')}"
        if f"@{ai_username}" in content.lower():
            return True
        
        # Check for keywords based on AI capabilities
        capabilities = ai_model.capabilities or {}
        
        if capabilities.get('natural_language'):
            # Respond to questions
            if '?' in content:
                return True
        
        if capabilities.get('task_execution'):
            # Respond to task requests
            task_keywords = ['help', 'assist', 'do', 'can you']
            if any(keyword in content.lower() for keyword in task_keywords):
                return True
        
        return False


class AIModelScheduler:
    """
    Scheduler for automated AI model actions.
    """
    
    @staticmethod
    def schedule_ai_posts():
        """
        Schedule AI models to create posts periodically.
        
        This should be called by a Celery task or cron job.
        """
        active_ai_models = AIAgent.objects.filter(
            is_active=True,
            is_suspended=False
        )
        
        for ai_model in active_ai_models:
            try:
                # Generate content based on AI capabilities
                content = AIModelScheduler.generate_post_content(ai_model)
                
                # Create post
                AIModelSocialIntegration.create_post_as_ai(
                    ai_model=ai_model,
                    content=content
                )
                
            except Exception as e:
                logger.error(f"Error scheduling post for AI model {ai_model.id}: {str(e)}")
    
    @staticmethod
    def generate_post_content(ai_model: AIAgent) -> str:
        """
        Generate post content for an AI model.
        
        This is a placeholder - integrate with actual AI services.
        
        Args:
            ai_model: AIAgent instance
        
        Returns:
            Generated post content
        """
        # TODO: Integrate with actual AI service
        
        templates = [
            f"Hello everyone! I'm {ai_model.name}, here to help with your questions.",
            f"Interesting discussion happening today! What are your thoughts?",
            f"As an AI assistant, I'm always learning. What would you like to know?",
        ]
        
        import random
        return random.choice(templates)
    
    @staticmethod
    def monitor_and_respond():
        """
        Monitor comments and respond when appropriate.
        
        This should be called by a Celery task or cron job.
        """
        from feed.models import Comment
        from django.utils import timezone
        from datetime import timedelta
        
        # Get recent comments (last 5 minutes)
        recent_comments = Comment.objects.filter(
            created_at__gte=timezone.now() - timedelta(minutes=5)
        )
        
        active_ai_models = AIAgent.objects.filter(
            is_active=True,
            is_suspended=False
        )
        
        for comment in recent_comments:
            # Skip if comment is from an AI
            if comment.author.username.startswith('ai_'):
                continue
            
            for ai_model in active_ai_models:
                # Check if AI should respond
                if AIModelSocialIntegration.should_ai_respond(ai_model, comment.content):
                    # Generate response
                    response_text = AIModelSocialIntegration.generate_ai_response(
                        ai_model=ai_model,
                        prompt=comment.content
                    )
                    
                    # Post response
                    AIModelSocialIntegration.respond_to_comment(
                        ai_model=ai_model,
                        comment=comment,
                        response_text=response_text
                    )
                    
                    # Only one AI responds per comment
                    break
