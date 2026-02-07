from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta, datetime
import random
import faker
from django.db import transaction
import urllib.request
import os
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Count
from itertools import islice, cycle
import time

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed the database with realistic test data for LinkedIn clone'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Number of users to create (default: 50)'
        )
        parser.add_argument(
            '--posts',
            type=int,
            default=200,
            help='Number of posts to create (default: 200)'
        )
        parser.add_argument(
            '--jobs',
            type=int,
            default=20,
            help='Number of job postings to create (default: 20)'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean existing test data before seeding'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        num_posts = options['posts']
        num_jobs = options['jobs']
        clean = options['clean']

        self.fake = faker.Faker()
        start_time = time.time()

        if clean:
            self.clean_test_data()
            self.stdout.write(self.style.SUCCESS('Cleaned existing test data'))

        with transaction.atomic():
            self.stdout.write('Creating test data...')
            
            # Create users
            users = self.create_users(num_users)
            self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users'))
            
            # Create experiences and education (bulk)
            self.create_experiences_and_education_bulk(users)
            self.stdout.write(self.style.SUCCESS('Created experiences and education'))
            
            # Create posts (bulk)
            posts = self.create_posts_bulk(users, num_posts)
            self.stdout.write(self.style.SUCCESS(f'Created {len(posts)} posts'))
            
            # Create jobs (bulk)
            jobs = self.create_jobs_bulk(users, num_jobs)
            self.stdout.write(self.style.SUCCESS(f'Created {len(jobs)} jobs'))
            
            # Create connections and follows (bulk)
            self.create_connections_and_follows_bulk(users)
            self.stdout.write(self.style.SUCCESS('Created connections and follows'))
            
            # Create comments and likes (bulk)
            self.create_comments_and_likes_bulk(posts, users)
            self.stdout.write(self.style.SUCCESS('Created comments and likes'))
            
            # Create messages (bulk)
            self.create_messages_bulk(users)
            self.stdout.write(self.style.SUCCESS('Created messages'))
            
            # Create job applications (bulk)
            self.create_applications_bulk(jobs, users)
            self.stdout.write(self.style.SUCCESS('Created job applications'))

        end_time = time.time()
        duration = end_time - start_time
        self.stdout.write(self.style.SUCCESS(f'Test data seeding completed successfully in {duration:.2f} seconds!'))

    def clean_test_data(self):
        """Clean all test data from the database"""
        from feed.models import Post, Comment
        from jobs.models import Job, Application
        from network.models import Connection, Follow
        from messaging.models import Message, Notification
        from users.models import Experience, Education, Report, Block

        # Delete in correct order to avoid foreign key constraints
        Message.objects.all().delete()
        Notification.objects.all().delete()
        Comment.objects.all().delete()
        Application.objects.all().delete()
        Job.objects.all().delete()
        Post.objects.all().delete()
        Connection.objects.all().delete()
        Follow.objects.all().delete()
        Experience.objects.all().delete()
        Education.objects.all().delete()
        Report.objects.all().delete()
        Block.objects.all().delete()
        
        # Delete test users (keep staff/superuser)
        User.objects.filter(is_staff=False, is_superuser=False).delete()

    def create_users(self, num_users):
        """Create realistic user profiles"""
        users = []
        
        # Create some specific professional profiles
        professional_profiles = [
            {
                'username': 'john_anderson',
                'first_name': 'John',
                'last_name': 'Anderson',
                'email': 'john.anderson@techcorp.com',
                'headline': 'Senior Software Engineer at TechCorp',
                'bio': 'Passionate software engineer with 10+ years of experience in full-stack development. Specialized in Python, Django, and cloud technologies.',
                'location': 'San Francisco, CA'
            },
            {
                'username': 'sarah_chen',
                'first_name': 'Sarah',
                'last_name': 'Chen',
                'email': 'sarah.chen@innovate.io',
                'headline': 'Product Manager at Innovate.io',
                'bio': 'Product manager focused on building innovative solutions for enterprise customers. Expertise in SaaS products and user experience design.',
                'location': 'New York, NY'
            },
            {
                'username': 'michael_rodriguez',
                'first_name': 'Michael',
                'last_name': 'Rodriguez',
                'email': 'm.rodriguez@designstudio.com',
                'headline': 'UX/UI Designer at Design Studio',
                'bio': 'Creative designer with a passion for user-centered design. 8 years of experience in creating beautiful and functional digital products.',
                'location': 'Austin, TX'
            },
            {
                'username': 'emily_watson',
                'first_name': 'Emily',
                'last_name': 'Watson',
                'email': 'emily.watson@datasci.com',
                'headline': 'Data Scientist at DataSci',
                'bio': 'Data scientist specializing in machine learning and artificial intelligence. PhD in Computer Science from MIT.',
                'location': 'Boston, MA'
            },
            {
                'username': 'david_kim',
                'first_name': 'David',
                'last_name': 'Kim',
                'email': 'david.kim@startuphub.com',
                'headline': 'CEO & Founder at StartupHub',
                'bio': 'Entrepreneur and tech enthusiast. Building the next generation of startup tools and resources.',
                'location': 'Seattle, WA'
            }
        ]

        # Create professional profiles
        for profile_data in professional_profiles:
            user = User.objects.create_user(
                username=profile_data['username'],
                email=profile_data['email'],
                first_name=profile_data['first_name'],
                last_name=profile_data['last_name'],
                password='password123'
            )
            user.profile.headline = profile_data['headline']
            user.profile.bio = profile_data['bio']
            user.profile.location = profile_data['location']
            # Add avatar for professional profiles (80% chance)
            if random.random() < 0.8:
                user.profile.avatar = self.get_fake_avatar(user.id)
            user.profile.save()
            users.append(user)

        # Create random users
        for i in range(num_users - len(professional_profiles)):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            username = f"{first_name.lower()}_{last_name.lower()}_{i}"
            email = self.fake.email()
            
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password='password123'
            )
            
            # Add profile information
            user.profile.headline = random.choice([
                f"{self.fake.job()} at {self.fake.company()}",
                f"Senior {self.fake.job()}",
                f"{self.fake.job()} | {self.fake.catch_phrase()}",
                f"Experienced {self.fake.job()} in {random.choice(['Technology', 'Finance', 'Healthcare', 'Education', 'Retail'])}"
            ])
            
            user.profile.bio = self.fake.text(max_nb_chars=200)
            user.profile.location = f"{self.fake.city()}, {self.fake.state_abbr()}"
            # Add avatar for random users (60% chance)
            if random.random() < 0.6:
                user.profile.avatar = self.get_fake_avatar(user.id)
            user.profile.save()
            users.append(user)

        return users

    def get_fake_avatar(self, user_id):
        """Generate a fake avatar image using a profile picture service"""
        try:
            # Use a service that provides profile pictures
            avatar_url = f"https://picsum.photos/200/200?random={user_id}"
            
            # Download the avatar
            urllib.request.urlretrieve(avatar_url, "temp_avatar.jpg")
            
            # Read the downloaded avatar
            with open("temp_avatar.jpg", 'rb') as f:
                avatar_data = f.read()
            
            # Clean up temp file
            if os.path.exists("temp_avatar.jpg"):
                os.remove("temp_avatar.jpg")
            
            return ContentFile(avatar_data, f"avatar_{user_id}.jpg")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not download avatar: {e}'))
            return None

    def get_fake_image(self, width=800, height=600):
        """Generate a fake image using Lorem Picsum"""
        try:
            # Use Lorem Picsum for random professional images
            image_url = f"https://picsum.photos/{width}/{height}?random={random.randint(1, 1000)}"
            
            # Download the image
            urllib.request.urlretrieve(image_url, "temp_image.jpg")
            
            # Read the downloaded image
            with open("temp_image.jpg", 'rb') as f:
                image_data = f.read()
            
            # Clean up temp file
            if os.path.exists("temp_image.jpg"):
                os.remove("temp_image.jpg")
            
            return ContentFile(image_data, f"post_image_{random.randint(1000, 9999)}.jpg")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not download image: {e}'))
            return None

    def create_experiences_and_education(self, users):
        """Create work experiences and education for users"""
        from users.models import Experience, Education
        
        for user in users:
            # Create 1-3 experiences per user
            num_experiences = random.randint(1, 3)
            for _ in range(num_experiences):
                start_date = self.fake.date_between(start_date='-10y', end_date='-1y')
                end_date = self.fake.date_between(start_date=start_date, end_date='today') if random.random() > 0.3 else None
                
                Experience.objects.create(
                    user=user,
                    title=self.fake.job(),
                    company=self.fake.company(),
                    location=f"{self.fake.city()}, {self.fake.state_abbr()}",
                    start_date=start_date,
                    end_date=end_date,
                    is_current=end_date is None,
                    description=self.fake.text(max_nb_chars=300)
                )
            
            # Create 1-2 education entries per user
            num_education = random.randint(1, 2)
            for _ in range(num_education):
                start_date = self.fake.date_between(start_date='-15y', end_date='-5y')
                end_date = self.fake.date_between(start_date=start_date, end_date='-3y')
                
                Education.objects.create(
                    user=user,
                    school=random.choice([
                        'Stanford University', 'MIT', 'Harvard University', 'UC Berkeley',
                        'Carnegie Mellon', 'University of Washington', 'Georgia Tech',
                        'University of Texas', 'UCLA', 'Columbia University'
                    ]),
                    degree=random.choice(['Bachelor of Science', 'Master of Science', 'PhD', 'MBA']),
                    field_of_study=random.choice([
                        'Computer Science', 'Business Administration', 'Engineering',
                        'Data Science', 'Design', 'Marketing', 'Economics'
                    ]),
                    start_date=start_date,
                    end_date=end_date,
                    description=self.fake.text(max_nb_chars=200)
                )

    def create_posts(self, users, num_posts):
        """Create professional posts"""
        from feed.models import Post
        
        posts = []
        post_templates = [
            "Excited to share that I've just completed {achievement}! This journey has been incredible and I've learned so much about {topic}. #professional #growth",
            "Just read an amazing article about {topic}. The insights on {specific_point} are game-changing for our industry. What are your thoughts? #innovation",
            "Looking back on my {time_period} at {company}, I'm grateful for the opportunities and challenges that helped me grow. Here's what I learned: {lesson} #career #reflection",
            "The future of {industry} is here! 🚀 Check out these {number} trends that are reshaping how we work: {trend1}, {trend2}, and {trend3}. #technology #future",
            "Proud to announce that our team at {company} just launched {product}! This wouldn't be possible without our amazing team. #teamwork #success",
            "Monday motivation: Remember that {quote}. Every expert was once a beginner. Keep pushing forward! #motivation #success",
            "Great discussion at {event} today! Key takeaways: {takeaway1} and {takeaway2}. The future of {industry} looks bright! #networking #learning",
            "Hiring alert! We're looking for a {role} to join our team at {company}. If you're passionate about {skill}, I'd love to hear from you! #hiring #careers"
        ]
        
        for _ in range(num_posts):
            user = random.choice(users)
            template = random.choice(post_templates)
            
            # Fill template with realistic data
            content = template.format(
                achievement=random.choice([
                    'a major project milestone', 'my certification exam', 'a successful product launch',
                    'a challenging course', 'a leadership training program'
                ]),
                topic=random.choice([
                    'artificial intelligence', 'sustainable technology', 'remote work',
                    'digital transformation', 'cloud computing', 'cybersecurity'
                ]),
                specific_point=random.choice([
                    'user experience design', 'data-driven decision making', 'agile methodologies',
                    'customer-centric approaches', 'innovation strategies'
                ]),
                time_period=random.choice(['year', '2 years', '3 years', '5 years']),
                company=self.fake.company(),
                lesson=random.choice([
                    'the importance of collaboration', 'resilience in challenging times',
                    'continuous learning', 'leadership skills', 'technical expertise'
                ]),
                industry=random.choice(['tech', 'finance', 'healthcare', 'education', 'retail']),
                number=random.choice(['3', '5', '7']),
                trend1=random.choice(['AI integration', 'remote collaboration', 'sustainability']),
                trend2=random.choice(['automation', 'blockchain', 'personalization']),
                trend3=random.choice(['data analytics', 'cloud migration', 'cybersecurity']),
                product=random.choice(['new platform', 'mobile app', 'AI tool', 'analytics dashboard']),
                quote=random.choice([
                    'success is a journey, not a destination',
                    'the only way to do great work is to love what you do',
                    'innovation distinguishes leaders from followers'
                ]),
                event=random.choice(['Tech Conference', 'Industry Summit', 'Workshop', 'Meetup']),
                takeaway1=random.choice(['collaboration is key', 'innovation drives growth']),
                takeaway2=random.choice(['user experience matters', 'data is the new oil']),
                role=random.choice(['Software Engineer', 'Product Manager', 'Designer', 'Data Scientist']),
                skill=random.choice(['technology', 'design', 'innovation', 'growth'])
            )
            
            # Add some random hashtags
            hashtags = random.sample([
                '#technology', '#innovation', '#leadership', '#career', '#growth',
                '#success', '#teamwork', '#motivation', '#learning', '#development'
            ], random.randint(2, 4))
            content += ' ' + ' '.join(hashtags)
            
            # Randomly add image to post (30% chance)
            post_image = None
            if random.random() < 0.3:  # 30% of posts will have images
                post_image = self.get_fake_image()
            
            post = Post.objects.create(
                user=user,
                content=content,
                image=post_image,
                created_at=self.fake.date_time_between(start_date='-6m', end_date='now')
            )
            posts.append(post)
        
        return posts

    def create_jobs(self, users, num_jobs):
        """Create job postings"""
        from jobs.models import Job
        
        jobs = []
        job_titles = [
            'Senior Software Engineer', 'Product Manager', 'UX Designer', 'Data Scientist',
            'DevOps Engineer', 'Frontend Developer', 'Backend Developer', 'Full Stack Developer',
            'Marketing Manager', 'Sales Representative', 'Business Analyst', 'Project Manager',
            'Technical Lead', 'Engineering Manager', 'Product Designer', 'Machine Learning Engineer',
            'Cloud Architect', 'Cybersecurity Analyst', 'Mobile Developer', 'QA Engineer',
            'Data Analyst', 'Marketing Specialist', 'Content Writer', 'HR Manager',
            'Financial Analyst', 'Operations Manager', 'Customer Success Manager', 'Sales Engineer'
        ]
        
        companies = [
            'TechCorp Solutions', 'InnovateTech Inc', 'DataDriven Systems', 'CloudFirst Technologies',
            'AI Innovations Lab', 'Digital Transformation Co', 'NextGen Software', 'FutureProof Systems',
            'SmartTech Solutions', 'Agile Development Group', 'Enterprise Software Inc', 'StartupHub',
            'GrowthEngine Technologies', 'Innovation Labs', 'TechVentures', 'Digital Dynamics',
            'Sparkle Solutions', 'NovaTech Inc', 'Apex Innovations', 'Pulse Technologies',
            'Fusion Systems', 'Catalyst Software', 'Nexus Innovations', 'Luminate Technologies',
            'Aurora Solutions', 'Pinnacle Software', 'Zephyr Innovations', 'Flux Technologies'
        ]
        
        job_descriptions = [
            "We are seeking a talented {title} to join our growing team. You will work on cutting-edge projects and collaborate with cross-functional teams.",
            "Join our innovative company as a {title}. This role offers excellent growth opportunities and chance to make a real impact.",
            "Looking for an experienced {title} to help us build future of technology. Competitive salary and great benefits included.",
            "Our fast-growing company needs a skilled {title}. You'll work with modern technologies and amazing team members.",
            "Exciting opportunity for a {title} to join our dynamic team. Remote-friendly environment with flexible work hours."
        ]
        
        requirements_templates = [
            "Bachelor's degree in relevant field or equivalent experience\n3+ years of experience in {field}\nStrong problem-solving skills\nExcellent communication abilities",
            "5+ years of professional experience\nProficiency in {skill1} and {skill2}\nExperience with {skill3}\nTeam player with leadership potential",
            "Master's degree preferred\n2+ years in similar role\nExpert knowledge of {field}\nAbility to work in fast-paced environment"
        ]
        
        for _ in range(num_jobs):
            poster = random.choice(users)
            title = random.choice(job_titles)
            company = random.choice(companies)
            
            # Generate realistic description
            description = random.choice(job_descriptions).format(title=title)
            
            # Generate requirements with specific skills
            requirements = random.choice(requirements_templates).format(
                field=random.choice(['software development', 'data analysis', 'product management', 'UX design', 'cloud computing']),
                skill1=random.choice(['Python', 'JavaScript', 'React', 'Django', 'AWS', 'Docker', 'Kubernetes']),
                skill2=random.choice(['PostgreSQL', 'MongoDB', 'Redis', 'MySQL', 'GraphQL', 'REST APIs']),
                skill3=random.choice(['Agile', 'Scrum', 'CI/CD', 'Microservices', 'DevOps'])
            )
            
            # Generate realistic salary ranges based on job type
            if 'Senior' in title or 'Lead' in title or 'Manager' in title:
                salary_range = f"${random.randint(120, 200)}k - ${random.randint(150, 250)}k"
            elif 'Engineer' in title or 'Developer' in title:
                salary_range = f"${random.randint(80, 140)}k - ${random.randint(100, 180)}k"
            elif 'Analyst' in title or 'Specialist' in title:
                salary_range = f"${random.randint(60, 100)}k - ${random.randint(80, 120)}k"
            else:
                salary_range = f"${random.randint(70, 120)}k - ${random.randint(90, 150)}k"
            
            job = Job.objects.create(
                title=title,
                company=company,
                location=f"{self.fake.city()}, {self.fake.state_abbr()}",
                workplace_type=random.choice(['remote', 'onsite', 'hybrid']),
                job_type=random.choice(['full-time', 'part-time', 'contract', 'internship']),
                description=description,
                requirements=requirements,
                salary_range=salary_range,
                posted_by=poster,
                created_at=self.fake.date_time_between(start_date='-3m', end_date='now')
            )
            jobs.append(job)
        
        return jobs

    def create_connections_and_follows(self, users):
        """Create connections and follows between users"""
        from network.models import Connection, Follow
        
        # Create connections
        for user in users:
            # Each user has 5-20 connections, but ensure we don't exceed available users
            max_connections = min(20, len(users) - 1)
            if max_connections > 0:
                num_connections = random.randint(min(5, max_connections), max_connections)
                potential_friends = [u for u in users if u != user]
                friends = random.sample(potential_friends, num_connections)
                
                for friend in friends:
                    # Avoid duplicate connections
                    if not Connection.objects.filter(
                        user=user, friend=friend
                    ).exists() and not Connection.objects.filter(
                        user=friend, friend=user
                    ).exists():
                        status = random.choice(['accepted', 'pending', 'accepted', 'accepted'])  # More accepted
                        Connection.objects.create(
                            user=user,
                            friend=friend,
                            status=status,
                            created_at=self.fake.date_time_between(start_date='-1y', end_date='now')
                        )
        
        # Create follows
        for user in users:
            # Each user follows 10-30 other users, but ensure we don't exceed available users
            max_follows = min(30, len(users) - 1)
            if max_follows > 0:
                num_follows = random.randint(min(10, max_follows), max_follows)
                potential_follows = [u for u in users if u != user]
                follows = random.sample(potential_follows, num_follows)
                
                for follow_user in follows:
                    # Avoid duplicate follows
                    if not Follow.objects.filter(
                        follower=user, followed=follow_user
                    ).exists():
                        Follow.objects.create(
                            follower=user,
                            followed=follow_user,
                            created_at=self.fake.date_time_between(start_date='-1y', end_date='now')
                        )

    def create_comments_and_likes(self, posts, users):
        """Create comments and likes on posts"""
        from feed.models import Comment
        
        for post in posts:
            # Create 0-10 comments per post
            num_comments = random.randint(0, 10)
            commenters = random.sample(users, min(num_comments, len(users)))
            
            for commenter in commenters:
                comment_templates = [
                    "Great insights! Thanks for sharing {name}.",
                    "I completely agree with this perspective. {point} is so important.",
                    "This really resonates with my experience. {thought}",
                    "Excellent points! Have you considered {suggestion}?",
                    "Love this approach! We've seen similar results in our work.",
                    "Interesting take on this topic. Looking forward to more content like this!",
                    "This is exactly what I needed to read today. Thank you!",
                    "Well said! The {industry} industry definitely needs more of this thinking."
                ]
                
                comment = random.choice(comment_templates).format(
                    name=post.user.first_name,
                    point=random.choice(['collaboration', 'innovation', 'user experience', 'data-driven decisions']),
                    thought=random.choice(['continuous learning', 'adaptability', 'strategic thinking']),
                    suggestion=random.choice(['exploring AI integration', 'focusing on sustainability', 'improving user engagement']),
                    industry=random.choice(['tech', 'business', 'design', 'marketing'])
                )
                
                Comment.objects.create(
                    post=post,
                    user=commenter,
                    content=comment,
                    created_at=self.fake.date_time_between(
                        start_date=post.created_at,
                        end_date='now'
                    )
                )
            
            # Create likes
            num_likes = random.randint(0, 20)
            likers = random.sample(users, min(num_likes, len(users)))
            post.likes.set(likers)

    def create_messages(self, users):
        """Create messages between users"""
        from messaging.models import Message
        
        # Create conversations between random pairs of users
        if len(users) >= 2:
            num_conversations = min(30, len(users) // 2)
            
            for _ in range(num_conversations):
                user1, user2 = random.sample(users, 2)
                
                # Create 1-10 messages per conversation
                num_messages = random.randint(1, 10)
                for i in range(num_messages):
                    sender = user1 if i % 2 == 0 else user2
                    recipient = user2 if i % 2 == 0 else user1
                    
                    message_templates = [
                        "Hi {name}, hope you're doing well!",
                        "Thanks for connecting! I'd love to learn more about your work at {company}.",
                        "Great post earlier! Really enjoyed your thoughts on {topic}.",
                        "Would you be interested in discussing {opportunity}?",
                        "Quick question about your experience with {skill}.",
                        "Congratulations on your recent achievement!",
                        "I saw you're looking for {role}. I might know someone perfect for this.",
                        "Let's catch up sometime soon! Are you available next week?"
                    ]
                    
                    content = random.choice(message_templates).format(
                        name=recipient.first_name,
                        company=self.fake.company(),
                        topic=random.choice(['AI', 'remote work', 'leadership', 'innovation']),
                        opportunity=random.choice(['collaboration', 'a potential project', 'career opportunities']),
                        skill=random.choice(['Python', 'product management', 'design thinking', 'data analysis']),
                        role=random.choice(['developers', 'designers', 'product managers'])
                    )
                    
                    Message.objects.create(
                        sender=sender,
                        recipient=recipient,
                        content=content,
                        status=random.choice(['sent', 'delivered', 'read']),
                        created_at=self.fake.date_time_between(start_date='-30d', end_date='now')
                    )

    def create_applications(self, jobs, users):
        """Create job applications"""
        from jobs.models import Application
        
        for job in jobs:
            # Create 0-15 applications per job
            num_applications = random.randint(0, 15)
            applicants = random.sample(users, min(num_applications, len(users)))
            
            for applicant in applicants:
                # Don't let the job poster apply to their own job
                if applicant != job.posted_by:
                    Application.objects.create(
                        job=job,
                        applicant=applicant,
                        cover_letter=self.fake.text(max_nb_chars=400),
                        status=random.choice(['pending', 'reviewed', 'interview', 'accepted', 'rejected']),
                        applied_at=self.fake.date_time_between(
                            start_date=job.created_at,
                            end_date='now'
                        )
                    )

    # BULK CREATION METHODS FOR OPTIMIZED PERFORMANCE
    
    def create_experiences_and_education_bulk(self, users):
        """Create experiences and education using bulk operations"""
        from users.models import Experience, Education
        
        experiences = []
        educations = []
        
        for user in users:
            # 1-3 experiences per user
            num_experiences = random.randint(1, 3)
            for _ in range(num_experiences):
                start_date = self.fake.date_between(start_date='-10y', end_date='-1y')
                end_date = self.fake.date_between(start_date=start_date, end_date='today') if random.random() > 0.3 else None
                
                experiences.append(Experience(
                    user=user,
                    company=self.fake.company(),
                    position=random.choice(['Software Engineer', 'Senior Developer', 'Product Manager', 'Data Scientist', 'Team Lead']),
                    description=self.fake.text(max_nb_chars=300),
                    start_date=start_date,
                    end_date=end_date,
                    current=end_date is None
                ))
            
            # 1-2 education entries per user
            num_education = random.randint(1, 2)
            for _ in range(num_education):
                start_date = self.fake.date_between(start_date='-15y', end_date='-5y')
                end_date = self.fake.date_between(start_date=start_date, end_date='-3y')
                
                educations.append(Education(
                    user=user,
                    institution=self.fake.company() + ' University',
                    degree=random.choice(['Bachelor', 'Master', 'PhD']) + ' in ' + random.choice(['Computer Science', 'Engineering', 'Business', 'Data Science']),
                    field_of_study=random.choice(['Computer Science', 'Engineering', 'Business Administration', 'Data Science']),
                    start_date=start_date,
                    end_date=end_date
                ))
        
        # Bulk create
        Experience.objects.bulk_create(experiences, batch_size=500)
        Education.objects.bulk_create(educations, batch_size=500)

    def create_posts_bulk(self, users, num_posts):
        """Create posts using bulk operations"""
        from feed.models import Post
        
        posts = []
        post_images = {}
        
        # Pre-generate some images
        num_images = max(1, num_posts // 3)  # 30% of posts have images
        for i in range(num_images):
            image = self.get_fake_image(800, 400)
            if image:
                post_images[i] = image
        
        for i in range(num_posts):
            user = random.choice(users)
            content = self.fake.text(max_nb_chars=500)
            
            # Add hashtags
            hashtags = random.sample([
                '#technology', '#innovation', '#leadership', '#career', '#growth',
                '#success', '#teamwork', '#motivation', '#learning', '#development'
            ], random.randint(2, 4))
            content += ' ' + ' '.join(hashtags)
            
            post = Post(
                user=user,
                content=content,
                created_at=self.fake.date_time_between(start_date='-30d', end_date='now')
            )
            
            # Add image to 30% of posts
            if random.random() < 0.3 and post_images:
                image_key = random.choice(list(post_images.keys()))
                post.image = post_images[image_key]
            
            posts.append(post)
        
        # Bulk create
        created_posts = Post.objects.bulk_create(posts, batch_size=100)
        return created_posts

    def create_jobs_bulk(self, users, num_jobs):
        """Create jobs using bulk operations"""
        from jobs.models import Job
        
        job_titles = [
            'Senior Software Engineer', 'Product Manager', 'Data Scientist', 'Frontend Developer',
            'Backend Developer', 'Full Stack Developer', 'DevOps Engineer', 'UX Designer',
            'Marketing Manager', 'Sales Representative', 'Business Analyst', 'Project Manager'
        ]
        
        companies = ['Google', 'Microsoft', 'Amazon', 'Apple', 'Meta', 'Netflix', 'Tesla', 'Spotify']
        locations = ['San Francisco', 'New York', 'London', 'Berlin', 'Tokyo', 'Remote']
        
        jobs = []
        
        for i in range(num_jobs):
            title = random.choice(job_titles)
            company = random.choice(companies)
            
            # Generate realistic salary ranges
            if 'Senior' in title or 'Lead' in title or 'Manager' in title:
                salary_range = f"${random.randint(120, 200)}k - ${random.randint(150, 250)}k"
            elif 'Engineer' in title or 'Developer' in title:
                salary_range = f"${random.randint(80, 140)}k - ${random.randint(100, 180)}k"
            elif 'Analyst' in title or 'Specialist' in title:
                salary_range = f"${random.randint(60, 100)}k - ${random.randint(80, 120)}k"
            else:
                salary_range = f"${random.randint(70, 120)}k - ${random.randint(90, 150)}k"
            
            jobs.append(Job(
                title=title,
                company=company,
                location=random.choice(locations),
                workplace_type=random.choice(['remote', 'onsite', 'hybrid']),
                job_type=random.choice(['full-time', 'part-time', 'contract']),
                description=self.fake.text(max_nb_chars=800),
                requirements=self.fake.text(max_nb_chars=400),
                salary_range=salary_range,
                posted_by=random.choice(users),
                status='active',
                created_at=self.fake.date_time_between(start_date='-60d', end_date='now')
            ))
        
        # Bulk create
        created_jobs = Job.objects.bulk_create(jobs, batch_size=100)
        return created_jobs

    def create_connections_and_follows_bulk(self, users):
        """Create connections and follows using bulk operations"""
        from network.models import Connection, Follow
        
        connections = []
        follows = []
        
        for user in users:
            # Connections
            max_connections = min(20, len(users) - 1)
            if max_connections > 0:
                num_connections = random.randint(min(5, max_connections), max_connections)
                potential_friends = [u for u in users if u != user]
                friends = random.sample(potential_friends, num_connections)
                
                for friend in friends:
                    connections.append(Connection(
                        user=user,
                        friend=friend,
                        status=random.choice(['accepted', 'pending', 'accepted', 'accepted']),
                        created_at=self.fake.date_time_between(start_date='-1y', end_date='now')
                    ))
            
            # Follows
            max_follows = min(30, len(users) - 1)
            if max_follows > 0:
                num_follows = random.randint(min(10, max_follows), max_follows)
                potential_follows = [u for u in users if u != user]
                follows_list = random.sample(potential_follows, num_follows)
                
                for follow_user in follows_list:
                    follows.append(Follow(
                        follower=user,
                        followed=follow_user,
                        created_at=self.fake.date_time_between(start_date='-1y', end_date='now')
                    ))
        
        # Bulk create
        Connection.objects.bulk_create(connections, batch_size=500)
        Follow.objects.bulk_create(follows, batch_size=500)

    def create_comments_and_likes_bulk(self, posts, users):
        """Create comments and likes using bulk operations"""
        from feed.models import Comment
        
        comments = []
        post_likes = {}
        
        for post in posts:
            # Comments
            num_comments = random.randint(0, 10)
            if num_comments > 0:
                commenters = random.sample(users, min(num_comments, len(users)))
                for commenter in commenters:
                    comments.append(Comment(
                        post=post,
                        user=commenter,
                        content=self.fake.text(max_nb_chars=200),
                        created_at=self.fake.date_time_between(start_date=post.created_at, end_date='now')
                    ))
            
            # Likes
            num_likes = random.randint(0, 20)
            if num_likes > 0:
                likers = random.sample(users, min(num_likes, len(users)))
                post_likes[post.id] = likers
        
        # Bulk create comments
        Comment.objects.bulk_create(comments, batch_size=500)
        
        # Set likes (need to fetch posts again after bulk creation)
        for post_id, likers in post_likes.items():
            Post.objects.filter(id=post_id).first().likes.set(likers)

    def create_messages_bulk(self, users):
        """Create messages using bulk operations"""
        from messaging.models import Message
        
        if len(users) < 2:
            return
        
        messages = []
        num_conversations = min(30, len(users) // 2)
        
        message_templates = [
            "Hi {name}, hope you're doing well!",
            "Thanks for connecting! I'd love to learn more about your work at {company}.",
            "Great post earlier! Really enjoyed your thoughts on {topic}.",
            "Would you be interested in discussing {opportunity}?",
            "Quick question about your experience with {skill}.",
            "Congratulations on your recent achievement!",
            "I saw you're looking for {role}. I might know someone perfect for this.",
            "Let's catch up sometime soon! Are you available next week?"
        ]
        
        for _ in range(num_conversations):
            user1, user2 = random.sample(users, 2)
            num_messages = random.randint(1, 10)
            
            for i in range(num_messages):
                sender = user1 if i % 2 == 0 else user2
                recipient = user2 if i % 2 == 0 else user1
                
                content = random.choice(message_templates).format(
                    name=recipient.first_name,
                    company=self.fake.company(),
                    topic=random.choice(['AI', 'remote work', 'leadership', 'innovation']),
                    opportunity=random.choice(['collaboration', 'a potential project', 'career opportunities']),
                    skill=random.choice(['Python', 'product management', 'design thinking', 'data analysis']),
                    role=random.choice(['developers', 'designers', 'product managers'])
                )
                
                messages.append(Message(
                    sender=sender,
                    recipient=recipient,
                    content=content,
                    status=random.choice(['sent', 'delivered', 'read']),
                    created_at=self.fake.date_time_between(start_date='-30d', end_date='now')
                ))
        
        # Bulk create
        Message.objects.bulk_create(messages, batch_size=500)

    def create_applications_bulk(self, jobs, users):
        """Create job applications using bulk operations"""
        from jobs.models import Application
        
        applications = []
        
        for job in jobs:
            num_applications = random.randint(0, 15)
            if num_applications > 0:
                applicants = random.sample(users, min(num_applications, len(users)))
                
                for applicant in applicants:
                    if applicant != job.posted_by:  # Don't let job poster apply to their own job
                        applications.append(Application(
                            job=job,
                            applicant=applicant,
                            cover_letter=self.fake.text(max_nb_chars=400),
                            status=random.choice(['pending', 'reviewed', 'interview', 'accepted', 'rejected']),
                            applied_at=self.fake.date_time_between(
                                start_date=job.created_at,
                                end_date='now'
                            )
                        ))
        
        # Bulk create
        Application.objects.bulk_create(applications, batch_size=500)
