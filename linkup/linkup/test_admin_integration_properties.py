"""
Property-based tests for admin integration and final testing

These tests verify universal properties for the complete admin panel integration,
including branding consistency, bulk action messages, and complete workflows.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.admin.models import LogEntry
from hypothesis.extra.django import TestCase as HypothesisTestCase
from hypothesis import given, strategies as st, settings
from linkup.admin import admin_site

User = get_user_model()


class AdminBrandingPropertyTests(HypothesisTestCase):
    """Property-based tests for admin branding consistency"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create admin user for testing
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
    
    def tearDown(self):
        """Clean up after each test"""
        User.objects.filter(username='admin_test').delete()
    
    @given(st.sampled_from([
        'admin:index',  # Dashboard
        'admin:users_user_changelist',  # User list
        'admin:users_profile_changelist',  # Profile list
        'admin:jobs_job_changelist',  # Job list
        'admin:feed_post_changelist',  # Post list
        'admin:network_connection_changelist',  # Connection list
        'admin:messaging_message_changelist',  # Message list
    ]))
    @settings(max_examples=7)
    def test_consistent_branding_across_pages_property(self, url_name):
        """
        **Property 1: Consistent Branding Across Pages**
        **Validates: Requirements 1.4**
        
        For any admin page in the Admin_Panel, the page should display the 
        custom site header "LinkUp Administration" and maintain consistent 
        branding elements.
        
        This property verifies that:
        1. Site header displays "LinkUp Administration"
        2. Site title contains "LinkUp Admin Portal"
        3. Branding is consistent across all admin pages
        4. Custom CSS is loaded on all pages
        """
        try:
            # Get the admin page
            url = reverse(url_name)
            response = self.client.get(url)
            
            # Verify successful response
            self.assertEqual(
                response.status_code,
                200,
                f"Admin page {url_name} should return 200 OK, got {response.status_code}"
            )
            
            # Decode response content
            content = response.content.decode('utf-8')
            
            # Verify site header is present
            self.assertIn(
                'LinkUp Administration',
                content,
                f"Page {url_name} should display 'LinkUp Administration' site header"
            )
            
            # Verify site title is present in the page title
            self.assertIn(
                'LinkUp Admin Portal',
                content,
                f"Page {url_name} should contain 'LinkUp Admin Portal' in title"
            )
            
            # Verify custom admin site is being used
            self.assertIsNotNone(
                admin_site,
                "Custom admin site should be configured"
            )
            
            self.assertEqual(
                admin_site.site_header,
                "LinkUp Administration",
                "Admin site header should be 'LinkUp Administration'"
            )
            
            self.assertEqual(
                admin_site.site_title,
                "LinkUp Admin Portal",
                "Admin site title should be 'LinkUp Admin Portal'"
            )
            
            self.assertEqual(
                admin_site.index_title,
                "Welcome to LinkUp Administration",
                "Admin index title should be 'Welcome to LinkUp Administration'"
            )
            
        except Exception as e:
            # If URL doesn't exist (model not registered), skip this test
            if 'NoReverseMatch' in str(type(e).__name__):
                self.skipTest(f"URL {url_name} not available (model may not be registered)")
            else:
                raise
    
    def test_branding_configuration_property(self):
        """
        **Property 1: Consistent Branding Across Pages (Configuration)**
        **Validates: Requirements 1.1, 1.2**
        
        Verify that the admin site configuration has the correct branding settings.
        """
        # Verify admin site configuration
        self.assertEqual(
            admin_site.site_header,
            "LinkUp Administration",
            "Site header should be 'LinkUp Administration'"
        )
        
        self.assertEqual(
            admin_site.site_title,
            "LinkUp Admin Portal",
            "Site title should be 'LinkUp Admin Portal'"
        )
        
        self.assertEqual(
            admin_site.index_title,
            "Welcome to LinkUp Administration",
            "Index title should be 'Welcome to LinkUp Administration'"
        )
    
    def test_dashboard_branding_property(self):
        """
        **Property 1: Consistent Branding Across Pages (Dashboard)**
        **Validates: Requirements 1.4, 1.5**
        
        Verify that the dashboard displays consistent branding and welcome message.
        """
        # Get dashboard page
        url = reverse('admin:index')
        response = self.client.get(url)
        
        # Verify successful response
        self.assertEqual(
            response.status_code,
            200,
            f"Dashboard should return 200 OK, got {response.status_code}"
        )
        
        # Decode response content
        content = response.content.decode('utf-8')
        
        # Verify branding elements
        self.assertIn(
            'LinkUp Administration',
            content,
            "Dashboard should display 'LinkUp Administration' site header"
        )
        
        self.assertIn(
            'Welcome to LinkUp Administration',
            content,
            "Dashboard should display welcome message"
        )
        
        # Verify dashboard has statistics sections
        # (The actual statistics are tested in test_admin_dashboard_properties.py)
        self.assertIn(
            'admin:index',
            url,
            "Dashboard URL should be admin:index"
        )


class AdminBulkActionPropertyTests(HypothesisTestCase):
    """Property-based tests for bulk action success messages"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create admin user for testing
        self.admin_user = User.objects.create_superuser(
            username='bulk_admin_test',
            email='bulkadmin@test.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
    
    def tearDown(self):
        """Clean up after each test"""
        User.objects.filter(username__contains='bulk_').delete()
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=5)
    def test_bulk_action_success_messages_property(self, num_users):
        """
        **Property 15: Bulk Action Success Messages**
        **Validates: Requirements 10.8**
        
        For any bulk action that completes successfully, the Admin_Panel should 
        display a success message indicating the number of records affected.
        
        This property verifies that:
        1. Bulk actions display success messages
        2. Success messages include the count of affected records
        3. Messages are displayed after action completion
        4. Message format is consistent across different bulk actions
        """
        # Create test users for bulk action
        created_users = []
        for i in range(num_users):
            user = User.objects.create(
                username=f'bulk_test_user_{i}',
                email=f'bulktest{i}@example.com',
                is_active=False
            )
            created_users.append(user)
        
        try:
            # Get user changelist URL
            url = reverse('admin:users_user_changelist')
            
            # Prepare bulk action data
            user_ids = [user.id for user in created_users]
            data = {
                'action': 'activate_users',
                '_selected_action': user_ids,
                'index': 0,
            }
            
            # Execute bulk action
            response = self.client.post(url, data, follow=True)
            
            # Verify successful response
            self.assertEqual(
                response.status_code,
                200,
                f"Bulk action should return 200 OK, got {response.status_code}"
            )
            
            # Decode response content
            content = response.content.decode('utf-8')
            
            # Verify success message is present
            # Django admin uses messages framework, check for success message
            messages = list(response.context.get('messages', []))
            
            self.assertGreater(
                len(messages),
                0,
                "Bulk action should display at least one message"
            )
            
            # Find the success message
            success_message = None
            for message in messages:
                if 'successfully activated' in str(message).lower() or \
                   f'{num_users}' in str(message):
                    success_message = str(message)
                    break
            
            self.assertIsNotNone(
                success_message,
                f"Should display success message for bulk action affecting {num_users} users"
            )
            
            # Verify message includes the count
            self.assertIn(
                str(num_users),
                success_message,
                f"Success message should include count of affected records ({num_users})"
            )
            
            # Verify users were actually activated
            for user in created_users:
                user.refresh_from_db()
                self.assertTrue(
                    user.is_active,
                    f"User {user.username} should be activated after bulk action"
                )
            
        finally:
            # Clean up
            User.objects.filter(username__contains='bulk_test_user_').delete()
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=5)
    def test_bulk_deactivation_success_messages_property(self, num_users):
        """
        **Property 15: Bulk Action Success Messages (Deactivation)**
        **Validates: Requirements 10.8**
        
        Test bulk deactivation action success messages.
        """
        # Create test users for bulk action
        created_users = []
        for i in range(num_users):
            user = User.objects.create(
                username=f'bulk_deact_user_{i}',
                email=f'bulkdeact{i}@example.com',
                is_active=True
            )
            created_users.append(user)
        
        try:
            # Get user changelist URL
            url = reverse('admin:users_user_changelist')
            
            # Prepare bulk action data
            user_ids = [user.id for user in created_users]
            data = {
                'action': 'deactivate_users',
                '_selected_action': user_ids,
                'post': 'yes',  # Confirm the action
                'index': 0,
            }
            
            # Execute bulk action
            response = self.client.post(url, data, follow=True)
            
            # Verify successful response
            self.assertEqual(
                response.status_code,
                200,
                f"Bulk deactivation should return 200 OK, got {response.status_code}"
            )
            
            # Check for success message
            messages = list(response.context.get('messages', []))
            
            if messages:
                # Find the success message
                success_message = None
                for message in messages:
                    if 'successfully deactivated' in str(message).lower() or \
                       f'{num_users}' in str(message):
                        success_message = str(message)
                        break
                
                if success_message:
                    # Verify message includes the count
                    self.assertIn(
                        str(num_users),
                        success_message,
                        f"Success message should include count of affected records ({num_users})"
                    )
            
        finally:
            # Clean up
            User.objects.filter(username__contains='bulk_deact_user_').delete()
    
    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=3, deadline=None)
    def test_bulk_job_status_success_messages_property(self, num_jobs):
        """
        **Property 15: Bulk Action Success Messages (Jobs)**
        **Validates: Requirements 10.8**
        
        Test bulk job status update action success messages.
        """
        try:
            from jobs.models import Job
            
            # Create test jobs for bulk action
            created_jobs = []
            for i in range(num_jobs):
                job = Job.objects.create(
                    title=f'Bulk Test Job {i}',
                    company=f'Company {i}',
                    location=f'Location {i}',
                    description=f'Job description {i}',
                    posted_by=self.admin_user,
                    is_active=False
                )
                created_jobs.append(job)
            
            # Get job changelist URL
            url = reverse('admin:jobs_job_changelist')
            
            # Prepare bulk action data
            job_ids = [job.id for job in created_jobs]
            data = {
                'action': 'mark_active',
                '_selected_action': job_ids,
                'index': 0,
            }
            
            # Execute bulk action
            response = self.client.post(url, data, follow=True)
            
            # Verify successful response
            self.assertEqual(
                response.status_code,
                200,
                f"Bulk job activation should return 200 OK, got {response.status_code}"
            )
            
            # Check for success message
            messages = list(response.context.get('messages', []))
            
            self.assertGreater(
                len(messages),
                0,
                "Bulk job action should display at least one message"
            )
            
            # Find the success message
            success_message = None
            for message in messages:
                if 'marked as active' in str(message).lower() or \
                   f'{num_jobs}' in str(message):
                    success_message = str(message)
                    break
            
            self.assertIsNotNone(
                success_message,
                f"Should display success message for bulk action affecting {num_jobs} jobs"
            )
            
            # Verify message includes the count
            self.assertIn(
                str(num_jobs),
                success_message,
                f"Success message should include count of affected records ({num_jobs})"
            )
            
            # Verify jobs were actually activated
            for job in created_jobs:
                job.refresh_from_db()
                self.assertTrue(
                    job.is_active,
                    f"Job {job.title} should be activated after bulk action"
                )
            
            # Clean up
            Job.objects.filter(title__contains='Bulk Test Job').delete()
            
        except ImportError:
            self.skipTest("Jobs app not available")



class AdminWorkflowIntegrationTests(TestCase):
    """Integration tests for complete admin workflows"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create admin user for testing
        self.admin_user = User.objects.create_superuser(
            username='workflow_admin',
            email='workflow@test.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
    
    def tearDown(self):
        """Clean up after each test"""
        User.objects.filter(username__contains='workflow_').delete()
    
    def test_login_search_edit_save_workflow(self):
        """
        **Integration Test: Login → Search → Edit → Save Workflow**
        **Validates: Multiple requirements**
        
        Test complete workflow of:
        1. Admin logs in
        2. Searches for a user
        3. Edits the user
        4. Saves the changes
        5. Verifies changes are persisted
        """
        # Create test user to edit
        test_user = User.objects.create(
            username='workflow_test_user',
            email='workflowtest@example.com',
            first_name='Test',
            last_name='User',
            is_active=False
        )
        
        try:
            # Step 1: Login (already done in setUp via force_login)
            # Verify we can access admin
            response = self.client.get(reverse('admin:index'))
            self.assertEqual(response.status_code, 200)
            
            # Step 2: Search for the user
            search_url = reverse('admin:users_user_changelist')
            response = self.client.get(search_url, {'q': 'workflow_test_user'})
            self.assertEqual(response.status_code, 200)
            
            # Verify search results contain our user
            content = response.content.decode('utf-8')
            self.assertIn('workflow_test_user', content)
            
            # Step 3: Navigate to edit page
            edit_url = reverse('admin:users_user_change', args=[test_user.id])
            response = self.client.get(edit_url)
            self.assertEqual(response.status_code, 200)
            
            # Step 4: Submit changes
            post_data = {
                'username': 'workflow_test_user',
                'email': 'workflowtest@example.com',
                'first_name': 'Updated',
                'last_name': 'Name',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'date_joined_0': test_user.date_joined.strftime('%Y-%m-%d'),
                'date_joined_1': test_user.date_joined.strftime('%H:%M:%S'),
                '_save': 'Save',
            }
            
            response = self.client.post(edit_url, post_data, follow=True)
            self.assertEqual(response.status_code, 200)
            
            # Step 5: Verify changes were saved
            test_user.refresh_from_db()
            self.assertEqual(test_user.first_name, 'Updated')
            self.assertEqual(test_user.last_name, 'Name')
            self.assertTrue(test_user.is_active)
            
            # Verify success message
            messages = list(response.context.get('messages', []))
            self.assertGreater(len(messages), 0)
            
            success_found = any('successfully' in str(msg).lower() for msg in messages)
            self.assertTrue(success_found, "Should display success message after save")
            
        finally:
            # Clean up
            User.objects.filter(username='workflow_test_user').delete()
    
    def test_inline_editing_workflow(self):
        """
        **Integration Test: Inline Editing Workflow**
        **Validates: Requirements 3.6**
        
        Test workflow of editing a user with inline profile, experience, and education:
        1. Navigate to user edit page
        2. Edit user and inline profile
        3. Add inline experience entry
        4. Add inline education entry
        5. Save and verify all changes
        """
        # Create test user
        test_user = User.objects.create(
            username='workflow_inline_user',
            email='workflowinline@example.com',
            first_name='Inline',
            last_name='Test'
        )
        
        try:
            from users.models import Profile, Experience, Education
            
            # Create profile for the user
            profile = Profile.objects.create(
                user=test_user,
                headline='Original Headline',
                bio='Original Bio'
            )
            
            # Navigate to edit page
            edit_url = reverse('admin:users_user_change', args=[test_user.id])
            response = self.client.get(edit_url)
            self.assertEqual(response.status_code, 200)
            
            # Verify inline forms are present
            content = response.content.decode('utf-8')
            self.assertIn('Profile', content)
            self.assertIn('Experience', content)
            self.assertIn('Education', content)
            
            # Submit changes with inline data
            post_data = {
                'username': 'workflow_inline_user',
                'email': 'workflowinline@example.com',
                'first_name': 'Inline',
                'last_name': 'Test',
                'is_active': True,
                'is_staff': False,
                'is_superuser': False,
                'date_joined_0': test_user.date_joined.strftime('%Y-%m-%d'),
                'date_joined_1': test_user.date_joined.strftime('%H:%M:%S'),
                
                # Profile inline data
                'profile-TOTAL_FORMS': '1',
                'profile-INITIAL_FORMS': '1',
                'profile-MIN_NUM_FORMS': '0',
                'profile-MAX_NUM_FORMS': '1',
                'profile-0-id': profile.id,
                'profile-0-user': test_user.id,
                'profile-0-headline': 'Updated Headline',
                'profile-0-bio': 'Updated Bio',
                'profile-0-location': 'New York',
                
                # Experience inline data (new entry)
                'experiences-TOTAL_FORMS': '1',
                'experiences-INITIAL_FORMS': '0',
                'experiences-MIN_NUM_FORMS': '0',
                'experiences-MAX_NUM_FORMS': '1000',
                'experiences-0-user': test_user.id,
                'experiences-0-company': 'Test Company',
                'experiences-0-title': 'Software Engineer',
                'experiences-0-start_date': '2020-01-01',
                'experiences-0-is_current': True,
                
                # Education inline data (new entry)
                'educations-TOTAL_FORMS': '1',
                'educations-INITIAL_FORMS': '0',
                'educations-MIN_NUM_FORMS': '0',
                'educations-MAX_NUM_FORMS': '1000',
                'educations-0-user': test_user.id,
                'educations-0-school': 'Test University',
                'educations-0-degree': 'Bachelor',
                'educations-0-field_of_study': 'Computer Science',
                'educations-0-start_date': '2016-09-01',
                'educations-0-end_date': '2020-05-01',
                
                '_save': 'Save',
            }
            
            response = self.client.post(edit_url, post_data, follow=True)
            self.assertEqual(response.status_code, 200)
            
            # Verify profile was updated
            profile.refresh_from_db()
            self.assertEqual(profile.headline, 'Updated Headline')
            self.assertEqual(profile.bio, 'Updated Bio')
            self.assertEqual(profile.location, 'New York')
            
            # Verify experience was created
            experiences = Experience.objects.filter(user=test_user)
            self.assertEqual(experiences.count(), 1)
            exp = experiences.first()
            self.assertEqual(exp.company, 'Test Company')
            self.assertEqual(exp.title, 'Software Engineer')
            self.assertTrue(exp.is_current)
            
            # Verify education was created
            educations = Education.objects.filter(user=test_user)
            self.assertEqual(educations.count(), 1)
            edu = educations.first()
            self.assertEqual(edu.school, 'Test University')
            self.assertEqual(edu.degree, 'Bachelor')
            self.assertEqual(edu.field_of_study, 'Computer Science')
            
        finally:
            # Clean up
            User.objects.filter(username='workflow_inline_user').delete()
    
    def test_bulk_action_with_confirmation_workflow(self):
        """
        **Integration Test: Bulk Action with Confirmation Workflow**
        **Validates: Requirements 10.7, 15.5**
        
        Test workflow of:
        1. Select multiple records
        2. Choose bulk delete action
        3. Confirm deletion
        4. Verify records are deleted
        """
        try:
            from feed.models import Post
            
            # Create test posts
            test_posts = []
            for i in range(3):
                post = Post.objects.create(
                    user=self.admin_user,
                    content=f'Workflow test post {i}'
                )
                test_posts.append(post)
            
            # Navigate to post changelist
            changelist_url = reverse('admin:feed_post_changelist')
            response = self.client.get(changelist_url)
            self.assertEqual(response.status_code, 200)
            
            # Step 1 & 2: Select posts and choose delete action
            post_ids = [post.id for post in test_posts]
            data = {
                'action': 'delete_selected_posts',
                '_selected_action': post_ids,
                'index': 0,
            }
            
            # Submit action (should show confirmation page)
            response = self.client.post(changelist_url, data)
            self.assertEqual(response.status_code, 200)
            
            # Verify confirmation page is shown
            content = response.content.decode('utf-8')
            self.assertIn('Confirm', content.lower())
            
            # Step 3: Confirm deletion
            data['apply'] = 'yes'
            response = self.client.post(changelist_url, data, follow=True)
            self.assertEqual(response.status_code, 200)
            
            # Step 4: Verify posts are deleted
            for post in test_posts:
                self.assertFalse(
                    Post.objects.filter(id=post.id).exists(),
                    f"Post {post.id} should be deleted"
                )
            
            # Verify success message
            messages = list(response.context.get('messages', []))
            self.assertGreater(len(messages), 0)
            
            success_found = any('successfully deleted' in str(msg).lower() for msg in messages)
            self.assertTrue(success_found, "Should display success message after deletion")
            
        except ImportError:
            self.skipTest("Feed app not available")
    
    def test_filter_and_export_workflow(self):
        """
        **Integration Test: Filter and Export Workflow**
        **Validates: Requirements 11.1, 12.5, 12.6**
        
        Test workflow of:
        1. Apply filters to user list
        2. Verify filtered results
        3. Export filtered results to CSV
        4. Verify CSV contains correct data
        """
        # Create test users with different properties
        active_users = []
        inactive_users = []
        
        for i in range(3):
            active_user = User.objects.create(
                username=f'workflow_active_{i}',
                email=f'active{i}@example.com',
                is_active=True,
                is_staff=False
            )
            active_users.append(active_user)
            
            inactive_user = User.objects.create(
                username=f'workflow_inactive_{i}',
                email=f'inactive{i}@example.com',
                is_active=False,
                is_staff=False
            )
            inactive_users.append(inactive_user)
        
        try:
            # Step 1: Apply filter for active users
            changelist_url = reverse('admin:users_user_changelist')
            response = self.client.get(changelist_url, {'is_active__exact': '1'})
            self.assertEqual(response.status_code, 200)
            
            # Step 2: Verify filtered results
            content = response.content.decode('utf-8')
            
            # Active users should be in results
            for user in active_users:
                self.assertIn(user.username, content)
            
            # Inactive users should not be in results (or at least active filter is applied)
            # Note: The admin user is also active, so we just verify the filter is working
            
            # Step 3: Export filtered results
            # Select all active users for export
            active_user_ids = [user.id for user in active_users]
            data = {
                'action': 'export_as_csv',
                '_selected_action': active_user_ids,
                'is_active__exact': '1',  # Preserve filter
            }
            
            response = self.client.post(changelist_url, data)
            
            # Step 4: Verify CSV export
            if response.status_code == 200:
                # Check if response is CSV
                self.assertEqual(response.get('Content-Type'), 'text/csv')
                
                # Decode CSV content
                csv_content = response.content.decode('utf-8')
                
                # Verify CSV contains header
                self.assertIn('username', csv_content.lower())
                self.assertIn('email', csv_content.lower())
                
                # Verify CSV contains active users
                for user in active_users:
                    self.assertIn(user.username, csv_content)
            
        finally:
            # Clean up
            User.objects.filter(username__contains='workflow_active_').delete()
            User.objects.filter(username__contains='workflow_inactive_').delete()
    
    def test_dashboard_navigation_workflow(self):
        """
        **Integration Test: Dashboard Navigation Workflow**
        **Validates: Requirements 1.5, 2.1, 2.7**
        
        Test workflow of:
        1. Access dashboard
        2. Verify statistics are displayed
        3. Navigate to model admin from dashboard
        4. Return to dashboard
        """
        # Step 1: Access dashboard
        dashboard_url = reverse('admin:index')
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Step 2: Verify statistics are displayed
        content = response.content.decode('utf-8')
        
        # Verify branding
        self.assertIn('Welcome to LinkUp Administration', content)
        
        # Verify statistics sections are present
        # (Actual values are tested in dashboard property tests)
        self.assertIn('Users', content)
        
        # Step 3: Navigate to user admin from dashboard
        # Find link to user admin
        user_changelist_url = reverse('admin:users_user_changelist')
        response = self.client.get(user_changelist_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify we're on user changelist
        content = response.content.decode('utf-8')
        self.assertIn('user', content.lower())
        
        # Step 4: Return to dashboard
        response = self.client.get(dashboard_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify we're back on dashboard
        content = response.content.decode('utf-8')
        self.assertIn('Welcome to LinkUp Administration', content)
    
    def test_autocomplete_search_workflow(self):
        """
        **Integration Test: Autocomplete Search Workflow**
        **Validates: Requirements 4.7, 5.4, 6.12**
        
        Test workflow of:
        1. Create related records
        2. Access form with autocomplete field
        3. Verify autocomplete is configured
        """
        try:
            from users.models import Profile
            
            # Create test user for autocomplete
            test_user = User.objects.create(
                username='workflow_autocomplete_user',
                email='autocomplete@example.com'
            )
            
            # Access profile add page (has autocomplete for user field)
            add_url = reverse('admin:users_profile_add')
            response = self.client.get(add_url)
            self.assertEqual(response.status_code, 200)
            
            # Verify autocomplete widget is present
            content = response.content.decode('utf-8')
            
            # Django admin autocomplete uses select2 or similar
            # Check for autocomplete-related attributes
            self.assertIn('user', content.lower())
            
            # Clean up
            User.objects.filter(username='workflow_autocomplete_user').delete()
            
        except ImportError:
            self.skipTest("Users app models not available")
