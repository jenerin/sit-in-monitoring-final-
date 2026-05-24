# CCS Sit-in Monitoring System

A web-based application for monitoring student sit-in sessions in computer laboratories.

## Features

- Student dashboard with sit-in tracking
- Session history and statistics
- PC reservation system
- Announcements and notifications
- Reward points system
- Testimonials
- Admin panel for managing students, sessions, reservations, and software applications
- Dark mode support

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd sit-in-monitoring
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

The application will be available at http://127.0.0.1:5000

## Default Credentials

- **Admin**: Username: `admin`, Password: `admin123`
- **Students**: Register through the registration page

## Database

The application uses SQLite for data persistence. The database file (`sitin_monitor.db`) will be created automatically on first run.

## Dark Mode

Dark mode is supported and can be toggled using the moon/sun icon in the top right corner of student pages.
