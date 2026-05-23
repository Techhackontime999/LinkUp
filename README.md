<div align="center">

# 🔗 LinkUp

### Full Stack Professional Network Platform

[![Django](https://img.shields.io/badge/Django-5.2.10-green.svg)](https://djangoproject.com)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-1.2.0-success.svg)](https://github.com/Techhackontime999/LinkUp/releases)
[![Status](https://img.shields.io/badge/Status-Released-brightgreen.svg)](https://github.com/Techhackontime999/LinkUp/releases)
[![GitHub stars](https://img.shields.io/github/stars/Techhackontime999/LinkUp?style=social)](https://github.com/Techhackontime999/LinkUp/stargazers)

**A modern, feature-rich professional networking platform built with Django, WebSockets, and Tailwind CSS.**

*Connecting professionals, one post at a time.*

[Features](#-features) · [Installation](#-installation) · [Tech Stack](#-tech-stack) · [Changelog](#-changelog) · [Roadmap](#-roadmap) · [Contributing](#-contributing)

</div>

---

## 🌟 Overview

**LinkUp** is a comprehensive professional networking platform designed to connect professionals, facilitate job opportunities, and enable meaningful interactions. Built independently using Python/Django and modern web technologies, it delivers a seamless experience for users to build their professional network — complete with real-time messaging, live notifications, job listings, and rich content creation.

> Built using **vibe coding** — the entire full-stack platform developed independently in Python, Django, Tailwind CSS, JavaScript, and Django Channels.

**Founded by:** [Techhackontime999](https://github.com/Techhackontime999) · amitkumarkh010102006@gmail.com

---

## ✨ Features

### 👤 User Management
- Secure registration and login system
- Comprehensive user profiles with avatars
- Work experience and educational background
- Skills and endorsements showcase

### 📝 Feed & Posts
- Rich text posts via CKEditor integration
- Image uploads and sharing
- Like, comment, edit, and delete posts
- Real-time feed updates

### 🤝 Networking
- Follow/unfollow system
- Connection requests
- User discovery and suggestions
- Public profile pages

### 💼 Jobs
- Browse and search job listings
- Post job openings (recruiters/companies)
- Apply to jobs directly through the platform
- Track and manage applications
- Saved jobs and job alerts

### 💬 Real-time Messaging
- Instant WebSocket-powered chat
- Typing indicators and read receipts
- Online/offline user status
- Offline message queuing
- Full conversation history

### 🔔 Notifications
- Real-time push notifications via WebSocket
- Types: likes, comments, follows, messages, job updates
- Customizable notification preferences
- Notification grouping and badge counts

### 🔍 Search
- Unified search across users, posts, and jobs
- Advanced filters and result highlighting
- Real-time suggestions
- Improved form rendering (v1.2.0)

### 🎨 UI/UX
- Fully responsive, mobile-first design
- Modern glassmorphism-inspired interface (Tailwind CSS)
- Smooth animations and skeleton loading states
- WCAG 2.1 AA accessibility compliant

### 🔒 Security
- CSRF protection on all forms
- XSS prevention with HTML sanitization (Bleach)
- Rate limiting per user/IP
- Secure session management
- File upload validation
- HSTS, X-Frame-Options, Content-Security-Policy headers

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 5.2.10, Python 3.10+ |
| **Database** | SQLite (dev) / PostgreSQL (production) |
| **Real-time** | Django Channels, Redis, WebSockets |
| **ASGI Server** | Daphne |
| **Frontend** | Tailwind CSS 4.2, Vanilla JS (ES6+) |
| **Rich Text** | CKEditor 6.7.3 |
| **Icons** | Heroicons (SVG) |
| **Image Processing** | Pillow |
| **HTML Sanitization** | Bleach |
| **File Detection** | Python-Magic |

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- Redis Server
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Techhackontime999/LinkUp.git
cd LinkUp

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start Redis (required for real-time features)
sudo systemctl start redis      # Linux
# brew services start redis     # macOS

# 5. Run database migrations
python3 manage.py makemigrations
python3 manage.py migrate

# 6. Create an admin account
python3 manage.py createsuperuser

# 7. Collect static files
python3 manage.py collectstatic --noinput

# 8. Install and build Tailwind CSS
python3 manage.py tailwind install
python3 manage.py tailwind build

# 9. Start the development server
python3 manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL for production)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=linkup_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Required environment variables for production

```bash
SECRET_KEY=your-secret-key
DEBUG=False
DJANGO_ENVIRONMENT=production
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://localhost:6379/0
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
```

---

## 📁 Project Structure

```
LinkUp/
├── core/                     # Security middleware, validators, search views
├── users/                    # Auth, profiles, experience, education
├── feed/                     # Posts, comments, likes
├── network/                  # Follow/connection system
├── jobs/                     # Job listings and applications
├── messaging/                # WebSocket consumers, real-time chat, notifications
├── theme/                    # Tailwind CSS source
├── professional_network/     # Django settings, URLs, ASGI/WSGI config
├── templates/                # Base templates
├── static/                   # CSS, JS, CKEditor assets
├── media/                    # User uploads (avatars, post images)
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🌐 Deployment

### Quick start (production)

```bash
# HTTP server
gunicorn professional_network.wsgi:application --config gunicorn.conf.py

# WebSocket server
daphne -b 0.0.0.0 -p 8001 professional_network.asgi:application
```

### Health check endpoints

| Endpoint | Purpose |
|---|---|
| `/health/` | Basic health check |
| `/health/db/` | Database connectivity |
| `/health/redis/` | Redis connectivity |
| `/readiness/` | Full readiness check |

### Deployment options
- **Heroku** — one-click deployment with add-ons
- **DigitalOcean** — App Platform or Droplet
- **AWS** — Elastic Beanstalk or EC2
- **Docker** — `docker-compose.yml` included

### Production checklist
- Set `DEBUG=False` and a strong `SECRET_KEY`
- Switch to PostgreSQL
- Configure Redis in production
- Run `collectstatic`
- Set up Nginx reverse proxy + SSL (Let's Encrypt)
- Enable HSTS and all security headers

---

## 📚 API Reference

### Posts

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/like/<post_id>/` | Like / unlike a post |
| `POST` | `/post/<post_id>/comment/` | Add a comment |
| `GET` | `/post/<post_id>/comments/` | Fetch all comments |
| `GET` | `/post/<post_id>/edit/` | Get post data for editing |
| `POST` | `/post/<post_id>/update/` | Save post edits |
| `POST` | `/post/<post_id>/delete/` | Delete a post |

### Network

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/follow/<user_id>/` | Follow / unfollow a user |

### WebSocket

```javascript
// Real-time chat
const chatSocket = new WebSocket('ws://localhost:8000/ws/chat/<username>/');

// Notifications
const notifSocket = new WebSocket('ws://localhost:8000/ws/notifications/');
```

---

## 🧪 Testing

```bash
# Run all tests
python3 manage.py test

# Run by app
python3 manage.py test users
python3 manage.py test feed
python3 manage.py test messaging

# With coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

---

## 📋 Changelog

### v1.2.0 — February 8, 2026 *(Latest)*

**Major features added:**
- Complete Job Management System — post, edit, delete jobs; applications, tracking, saved jobs, and alerts
- Enhanced Search — fixed template syntax errors, improved UI and form rendering
- Admin Test Data Management — seed/clear commands and data migration tools

**Technical fixes:**
- Template rendering issues resolved
- Form validation improvements
- CSS class simplification
- Better error handling

---

### v1.1.0 — February 6, 2026

**Real-time messaging fix:**

Resolved critical WebSocket event handling issues preventing real-time message display in chat. Messages were only appearing after a page refresh.

**Root cause:** Django Channels WebSocket consumers were missing handlers for several event types — `multi_tab_sync`, `notification_message`, `user_status`, `read_receipt_update`, and `badge_update` — causing `ValueError: No handler for message type X` and connection drops.

**Fix:** Added all missing event handlers to both `ChatConsumer` and `NotificationsConsumer` in `linkup/messaging/consumers.py` (+60 lines).

**Impact:**
- Messages now appear instantly for both sender and receiver
- No more WebSocket connection drops
- Cross-tab synchronization, read receipts, and badge updates all functioning correctly

---

### v1.0.0 — February 4, 2026 *(Initial Release)*

First official release of LinkUp.

**Core platform delivered:**
- User authentication, profiles, experience, and education
- Rich text post creation with image sharing (CKEditor)
- Like, comment, edit, delete on posts
- Follow/connection system and user discovery
- Job listings and application tracking
- Real-time WebSocket messaging with typing indicators and read receipts
- Live notification system
- Unified search across users, posts, and jobs
- Django admin panel with content moderation
- Full security hardening (CSRF, XSS, rate limiting, HSTS)
- Production-ready deployment (PostgreSQL, Redis, Daphne, Docker, Nginx)

---

## 🗺️ Roadmap

| Version | Status | Features |
|---|---|---|
| v1.0.0 | ✅ Released | Auth, posts, messaging, jobs, notifications, search |
| v1.1.0 | ✅ Released | Real-time messaging WebSocket fix |
| v1.2.0 | ✅ Released | Job management, enhanced search, admin tools |
| v1.3.0 | 🔵 Planned | Video posts, Stories, advanced analytics |
| v2.0.0 | 🔵 Future | Groups, events, premium subscriptions, company pages, learning platform |

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit using conventional format: `feat: add user profile editing`
4. Push and open a Pull Request

**Commit types:** `feat` · `fix` · `docs` · `style` · `refactor` · `test` · `chore`

**Areas to contribute:** bug fixes, new features, documentation, UI/UX, performance, security, tests, translations.

---

## 🐛 Troubleshooting

**Redis connection error**
```bash
redis-cli ping   # Should return PONG
sudo systemctl start redis
```

**Static files not loading**
```bash
python3 manage.py collectstatic --noinput
```

**WebSocket not connecting** — verify Redis is running and `CHANNEL_LAYERS` is configured in `settings.py`.

**Rate limit exceeded (429)**
```bash
python3 clear_rate_limit.py
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 📞 Contact & Support

- **Bug reports:** [GitHub Issues](https://github.com/Techhackontime999/LinkUp/issues)
- **Discussions:** [GitHub Discussions](https://github.com/Techhackontime999/LinkUp/discussions)
- **Email:** amitkumarkh010102006@gmail.com

---

<div align="center">

**Made with ❤️ by [Techhackontime999](https://github.com/Techhackontime999)**

⭐ Star this repo if you find it useful!

[⬆ Back to top](#-linkup)

</div>
