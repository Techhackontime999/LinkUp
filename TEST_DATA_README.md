# Test Data Seeding System for LinkUp

This document explains how to use the test data seeding system for your LinkedIn clone project.

## Overview

The test data seeding system allows you to quickly populate your LinkUp application with realistic test data that makes the website feel active and professional - perfect for video recordings, demos, and testing.

## Features

- **Realistic User Profiles**: Creates professional users with complete profiles including work experience, education, and professional headlines
- **Professional Posts**: Generates authentic LinkedIn-style posts with relevant hashtags and professional content
- **Job Postings**: Creates realistic job listings with applications
- **Social Interactions**: Adds connections, follows, likes, and comments
- **Messaging**: Generates private messages between users
- **One-Click Management**: Easy commands to create and drop all test data

## Installation

1. Install the required faker package:
```bash
pip install faker>=18.0.0
```

2. Make sure your Django environment is properly set up and you can run management commands.

## Usage

### Seed Test Data

Generate test data with default settings (50 users, 200 posts, 20 jobs):
```bash
python manage.py seed_test_data
```

### Custom Parameters

You can customize the amount of data generated:

```bash
# Create 100 users, 500 posts, and 50 jobs
python manage.py seed_test_data --users 100 --posts 500 --jobs 50

# Clean existing data before seeding
python manage.py seed_test_data --clean
```

### Drop Test Data

Remove all test data (keeps staff/superuser accounts):
```bash
# Interactive mode (asks for confirmation)
python manage.py drop_test_data

# Skip confirmation (useful for scripts)
python manage.py drop_test_data --confirm
```

## Generated Data Details

### Users
- **Professional Profiles**: 5 specific professional users with detailed profiles
- **Random Users**: Configurable number of additional users with realistic data
- **Profile Information**: Headlines, bios, locations, and profile pictures
- **Work Experience**: 1-3 work experiences per user with realistic job titles and companies
- **Education**: 1-2 education entries per user from prestigious universities

### Posts
- **Professional Content**: LinkedIn-style posts with industry-relevant topics
- **Hashtags**: Appropriate professional hashtags for better visibility
- **Engagement**: Realistic timestamps and engagement patterns
- **Variety**: Different post types including achievements, insights, questions, and announcements

### Jobs
- **Realistic Listings**: Professional job postings with requirements and salary ranges
- **Variety**: Different job types (remote, onsite, hybrid) and employment types
- **Applications**: Random applications with different statuses

### Social Features
- **Connections**: Network connections between users with different statuses
- **Follows**: User follows to simulate professional networking
- **Comments**: Engaging comments on posts with professional tone
- **Likes**: Like interactions on posts
- **Messages**: Private messages between connected users

## Default Test Users

The system creates 5 specific professional users that you can use for testing:

1. **john_anderson** - Senior Software Engineer at TechCorp
2. **sarah_chen** - Product Manager at Innovate.io  
3. **michael_rodriguez** - UX/UI Designer at Design Studio
4. **emily_watson** - Data Scientist at DataSci
5. **david_kim** - CEO & Founder at StartupHub

All test users have the password: `password123`

## Best Practices for Video Recording

1. **Run with Clean Data**: Use the `--clean` flag to start fresh
2. **Generate Sufficient Data**: Use higher numbers for more realistic activity
   ```bash
   python manage.py seed_test_data --users 100 --posts 500 --jobs 50 --clean
   ```

3. **Login as Test Users**: Use the professional profiles for demonstrations
4. **Check Timestamps**: Posts and activities have realistic timestamps over the past 6 months

## File Structure

```
linkup/
├── linkup/
│   └── management/
│       └── commands/
│           ├── seed_test_data.py    # Main seeding command
│           └── drop_test_data.py     # Data cleanup command
├── requirements_test_data.txt        # Additional requirements
└── TEST_DATA_README.md              # This documentation
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure faker is installed
   ```bash
   pip install faker>=18.0.0
   ```

2. **Permission Error**: Ensure your database user has write permissions

3. **Memory Issues**: For very large datasets, consider generating data in smaller batches

### Customization

You can easily customize the generated data by modifying the templates and lists in `seed_test_data.py`:

- **User Profiles**: Edit `professional_profiles` and random user generation
- **Post Templates**: Modify `post_templates` for different content styles
- **Job Titles**: Update `job_titles` list for your industry
- **Message Templates**: Edit `message_templates` for different conversation styles

## Security Notes

- All test users use the same password: `password123`
- Test data includes fake emails and information
- The `drop_test_data` command preserves staff and superuser accounts
- Never use these credentials in production

## Performance Considerations

- Large datasets may take time to generate
- Database indexes are automatically utilized
- Transactions ensure data consistency
- Memory usage scales with the amount of data generated

## Support

For issues or questions about the test data seeding system, check the Django management command documentation or modify the seed files to suit your specific needs.
