# Clothing Business Notification System

## Overview
The notification system automatically alerts clothing business owners about important events in their business operations.

## Notification Types

### 1. OFFER_CREATED
- **Trigger**: When a new offer is created
- **Auto-generated**: Yes (on offer creation)
- **Message**: Shows offer details, discount amount, and validity period

### 2. OFFER_EXPIRING
- **Trigger**: When an offer is about to expire (within 3 days)
- **Auto-generated**: Via management command
- **Command**: `python manage.py check_expiring_offers`
- **Message**: Shows days remaining and offer details

### 3. OFFER_EXPIRED
- **Trigger**: When an offer has expired
- **Auto-generated**: Via management command
- **Command**: `python manage.py check_expiring_offers`
- **Message**: Notifies that offer has expired
- **Action**: Automatically updates offer status to 'EXPIRED'

### 4. LOW_STOCK
- **Trigger**: When item stock falls below reorder level
- **Auto-generated**: Via management command
- **Command**: `python manage.py check_low_stock`
- **Message**: Lists items running low on stock
- **Frequency**: Once per day per business

### 5. PURCHASE_RECEIVED
- **Trigger**: When a purchase order is received (full or partial)
- **Auto-generated**: Yes (on purchase receive)
- **Message**: Shows supplier name and total amount

### 6. GENERAL
- **Trigger**: For general updates (offer updates, deletions, etc.)
- **Auto-generated**: Yes (on various actions)
- **Message**: Varies based on action

## How Notifications Work

### Automatic Notifications
These are created automatically when certain actions occur:
- Creating a new offer
- Updating an offer
- Deleting an offer
- Receiving a purchase order

### Scheduled Notifications
These require management commands to be run (typically via cron job):

#### Daily Tasks
```bash
# Check for low stock items (run once daily)
python manage.py check_low_stock

# Check for expiring/expired offers (run once daily)
python manage.py check_expiring_offers
```

#### Setting up Cron Jobs (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add these lines (adjust path to your project)
# Run at 9 AM every day
0 9 * * * cd /path/to/POSsystem && python manage.py check_low_stock
0 9 * * * cd /path/to/POSsystem && python manage.py check_expiring_offers
```

#### Setting up Task Scheduler (Windows)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to Daily at 9:00 AM
4. Action: Start a program
5. Program: `python`
6. Arguments: `manage.py check_low_stock`
7. Start in: `C:\path\to\POSsystem`
8. Repeat for `check_expiring_offers`

## Notification Display

### Location
Notifications appear in the top navigation bar (bell icon) for clothing businesses only.

### Features
- Red badge shows unread notification count
- Dropdown shows last 3 notifications
- Unread notifications have blue background
- Click notification to mark as read and navigate to related page
- "Mark all as read" option available

### Notification Retention
- Notifications from last 30 days are shown
- Older notifications are still in database but not displayed

## Testing Notifications

### Test Script
```bash
python test_notifications.py
```

This script shows:
- Current notification count
- All notifications for logged-in user's business
- Read/unread status
- Available notification types

### Manual Testing
1. Create a new offer → Should create OFFER_CREATED notification
2. Update an offer → Should create GENERAL notification
3. Delete an offer → Should create GENERAL notification
4. Receive a purchase → Should create PURCHASE_RECEIVED notification
5. Run `check_expiring_offers` → Should create OFFER_EXPIRING notifications
6. Run `check_low_stock` → Should create LOW_STOCK notifications (if applicable)

## Database Schema

### Notification Model
```python
class Notification(models.Model):
    business = ForeignKey(Business)
    notification_type = CharField(choices=NOTIFICATION_TYPES)
    title = CharField(max_length=200)
    message = TextField()
    link = CharField(max_length=500, blank=True)
    is_read = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
```

## API Endpoints

### Mark Notification as Read
```
GET /notifications/<notification_id>/read/
```
- Marks notification as read
- Redirects to notification link or previous page

### Mark All Notifications as Read
```
GET /notifications/mark-all-read/
```
- Marks all unread notifications as read for current business
- Redirects to previous page

## Context Processor

The `notifications` context processor in `core/context_processors.py` provides:
- `recent_notifications`: Last 3 notifications (from last 30 days)
- `unread_notifications_count`: Count of unread notifications
- `current_business`: Current user's business
- `current_business_type`: Business type (e.g., 'clothing')

Available in all templates automatically.

## Troubleshooting

### Notifications not showing
1. Check if user is logged in
2. Check if user has a business assigned
3. Check if business type is 'Clothing'
4. Check browser console for JavaScript errors
5. Verify context processor is in settings.py

### Notifications not being created
1. Check if management commands are running
2. Check database for Notification records
3. Check application logs for errors
4. Run `python test_notifications.py` to debug

### Badge not updating
1. Refresh the page
2. Check if JavaScript is enabled
3. Check browser console for errors
4. Verify notification count in database

## Future Enhancements

Potential improvements:
- Real-time notifications using WebSockets
- Email notifications for critical alerts
- SMS notifications for urgent matters
- Notification preferences per user
- Notification history page
- Bulk notification actions
- Notification categories/filters
