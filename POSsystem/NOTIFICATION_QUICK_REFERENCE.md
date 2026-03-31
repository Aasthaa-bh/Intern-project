# Notification System - Quick Reference Guide

## Creating Notifications

### Basic Template
```python
from clothing.models import Notification

Notification.objects.create(
    business=business,                    # Required: Business object
    notification_type='TYPE',             # Required: See types below
    target_role='ROLE',                   # Required: ADMIN, CASHIER, or ALL
    title='Notification Title',           # Required: Short title
    message='Detailed message here',      # Required: Full message
    link='/path/to/page/',               # Optional: Link to related page
    is_read=False                        # Default: False
)
```

## Notification Types

| Type | Description | Default Target |
|------|-------------|----------------|
| `OFFER_CREATED` | New offer created | ADMIN |
| `OFFER_EXPIRING` | Offer expiring soon | ADMIN |
| `OFFER_EXPIRED` | Offer has expired | ADMIN |
| `LOW_STOCK` | Stock below reorder level | ADMIN |
| `PURCHASE_RECEIVED` | Purchase order received | ADMIN |
| `PAYMENT_COMPLETED` | Payment successful | ADMIN + CASHIER |
| `PAYMENT_FAILED` | Payment cancelled/failed | ADMIN + CASHIER |
| `GENERAL` | General announcements | ADMIN (or ALL) |

## Target Roles

| Role | Who Sees It | Use Case |
|------|-------------|----------|
| `ADMIN` | Owner, SuperAdmin | Business management notifications |
| `CASHIER` | Cashier | Operational notifications |
| `ALL` | Everyone | Important announcements |

## Common Examples

### 1. Low Stock Alert (Admin Only)
```python
Notification.objects.create(
    business=business,
    notification_type='LOW_STOCK',
    target_role='ADMIN',
    title=f'Low Stock Alert: {count} items',
    message=f'Items running low: {item_list}',
    link='/clothing/low-stock/',
    is_read=False
)
```

### 2. Payment Success (Both Admin & Cashier)
```python
# For Admin
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_COMPLETED',
    target_role='ADMIN',
    title='Payment Received',
    message=f'Payment of Rs {amount} completed. Txn: {txn_code}',
    link='',
    is_read=False
)

# For Cashier
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_COMPLETED',
    target_role='CASHIER',
    title='Payment Confirmed',
    message=f'Customer payment of Rs {amount} confirmed. Txn: {txn_code}',
    link='',
    is_read=False
)
```

### 2b. Payment Failed/Cancelled (Both Admin & Cashier)
```python
# For Admin
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_FAILED',
    target_role='ADMIN',
    title='Payment Failed',
    message=f'Payment cancelled or failed. Amount: Rs {amount}. Txn: {txn_uuid}',
    link='',
    is_read=False
)

# For Cashier
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_FAILED',
    target_role='CASHIER',
    title='Payment Cancelled',
    message=f'Customer payment was cancelled or failed. Amount: Rs {amount}. Txn: {txn_uuid}',
    link='',
    is_read=False
)
```

### 3. Offer Created (Admin Only)
```python
Notification.objects.create(
    business=business,
    notification_type='OFFER_CREATED',
    target_role='ADMIN',
    title=f'New Offer: {offer.offer_name}',
    message=f'{offer.get_offer_type_display()} - {offer.get_discount_display()}',
    link=f'/clothing/offers/{offer.id}/',
    is_read=False
)
```

### 4. Purchase Received (Admin Only)
```python
Notification.objects.create(
    business=business,
    notification_type='PURCHASE_RECEIVED',
    target_role='ADMIN',
    title=f'Purchase Received: {supplier_name}',
    message=f'Purchase #{purchase_id} received. Total: Rs {amount}',
    link=f'/clothing/purchases/{purchase_id}/',
    is_read=False
)
```

### 5. General Announcement (All Users)
```python
Notification.objects.create(
    business=business,
    notification_type='GENERAL',
    target_role='ALL',
    title='Important Announcement',
    message='System maintenance scheduled for Sunday 2AM-4AM',
    link='',
    is_read=False
)
```

## Filtering Notifications (Context Processor)

The system automatically filters notifications based on user role:

```python
# In core/context_processors.py
if user_role in ['SUPERADMIN', 'OWNER']:
    # Shows ADMIN + ALL notifications
    role_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
elif user_role == 'CASHIER':
    # Shows CASHIER + ALL notifications
    role_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
else:
    # Shows only ALL notifications
    role_filter = Q(target_role='ALL')
```

## Best Practices

1. **Choose the Right Target Role**
   - Business decisions → `ADMIN`
   - Daily operations → `CASHIER`
   - Important announcements → `ALL`

2. **Keep Titles Short**
   - Max 50 characters
   - Clear and actionable

3. **Provide Context in Messages**
   - Include relevant details (amounts, dates, names)
   - Keep under 200 characters

4. **Use Links Wisely**
   - Link to relevant pages when possible
   - Use empty string `''` if no link needed

5. **Don't Spam**
   - Check for existing notifications before creating duplicates
   - Use daily limits for recurring notifications (like low stock)

## Testing

Run the test script to verify notifications:
```bash
python test_role_notifications.py
```

Create sample notifications:
```bash
python create_sample_role_notifications.py
```

## Troubleshooting

### Notifications not showing?
1. Check user is logged in
2. Verify user has a business assigned
3. Check business type is 'Clothing'
4. Verify user role matches notification target_role
5. Check notification created_at is within 30 days

### Wrong notifications showing?
1. Verify target_role is set correctly
2. Check context processor filtering logic
3. Ensure migration is applied: `python manage.py migrate clothing`

## Migration

If you need to apply the migration:
```bash
python manage.py migrate clothing
```

This adds the `target_role` field to the Notification model.

---

**Last Updated**: March 31, 2026
**Version**: 2.0 (Role-Based)
