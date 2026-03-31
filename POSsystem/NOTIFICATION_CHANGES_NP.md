# Notification System - Role-Based Updates

## के भयो? (What Changed?)

Notification system ma role-based filtering add gareko cha. Aba different users le afno role anusar notifications dekhcha.

## Notification Distribution

### 1. Admin (Owner/SuperAdmin) lai jane notifications:
- ✅ **Low Stock Alert** - Stock kam bhayo bhane
- ✅ **Payment Completed** - Payment successful bhayo bhane (Admin version)
- ✅ **Payment Failed** - Payment cancel/fail bhayo bhane (Admin version)
- ✅ **Offer Created** - Naya offer banayo bhane
- ✅ **Offer Updated** - Offer update bhayo bhane
- ✅ **Offer Deleted** - Offer delete bhayo bhane
- ✅ **Offer Expiring** - Offer expire huna lako cha bhane
- ✅ **Offer Expired** - Offer expire bhaisakyo bhane
- ✅ **Purchase Received** - Purchase order receive bhayo bhane

### 2. Cashier lai jane notifications:
- ✅ **Payment Confirmed** - Customer ko payment successful bhayo bhane (Cashier version)
- ✅ **Payment Cancelled** - Customer ko payment cancel/fail bhayo bhane (Cashier version)

### 3. All Users lai jane notifications:
- ✅ **General Announcements** - Sabai lai dekhine general messages

## Technical Changes

### 1. Database Model Update
```python
# Notification model ma naya field add bhayo:
target_role = CharField(choices=TARGET_ROLES, default='ADMIN')

# Target roles:
- 'ADMIN' - Owner/SuperAdmin lai
- 'CASHIER' - Cashier lai
- 'ALL' - Sabai lai
```

### 2. Context Processor Update
`core/context_processors.py` ma automatic filtering add bhayo:
- Owner/SuperAdmin: ADMIN + ALL notifications dekhcha
- Cashier: CASHIER + ALL notifications dekhcha
- Other roles: ALL notifications matra dekhcha

### 3. Updated Files
1. `clothing/models.py` - Notification model updated
2. `core/context_processors.py` - Role-based filtering added
3. `clothing/views_payment.py` - Payment notifications for both Admin & Cashier
4. `clothing/views_offer.py` - Offer notifications for Admin
5. `clothing/views.py` - Purchase notifications for Admin
6. `clothing/management/commands/check_low_stock.py` - Low stock for Admin
7. `clothing/management/commands/check_expiring_offers.py` - Offer expiry for Admin

### 4. Migration
```bash
python manage.py migrate clothing
```
Migration successfully run bhaisakyo.

## Testing

Test script banako cha:
```bash
python test_role_notifications.py
```

Test results:
- ✅ Admin users: 9 notifications dekhyo (ADMIN + ALL)
- ✅ Cashier users: 2 notifications dekhyo (CASHIER + ALL)
- ✅ Filtering correctly working

## Example Usage

### Payment Success ma:
```python
# Admin lai
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_COMPLETED',
    target_role='ADMIN',
    title='Payment Received',
    message=f'Payment of Rs {amount} completed successfully.'
)

# Cashier lai
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_COMPLETED',
    target_role='CASHIER',
    title='Payment Confirmed',
    message=f'Customer payment of Rs {amount} has been confirmed.'
)
```

### Payment Cancel/Fail ma:
```python
# Admin lai
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_FAILED',
    target_role='ADMIN',
    title='Payment Failed',
    message=f'Payment cancelled or failed. Amount: Rs {amount}.'
)

# Cashier lai
Notification.objects.create(
    business=business,
    notification_type='PAYMENT_FAILED',
    target_role='CASHIER',
    title='Payment Cancelled',
    message=f'Customer payment was cancelled or failed. Amount: Rs {amount}.'
)
```

### Low Stock Alert ma:
```python
# Admin lai matra
Notification.objects.create(
    business=business,
    notification_type='LOW_STOCK',
    target_role='ADMIN',
    title=f'Low Stock Alert: {count} items',
    message=f'Items running low: {items_list}'
)
```

## Benefits

1. **Relevant Notifications**: Har user le afno kaam ko notifications matra dekhcha
2. **Less Clutter**: Unnecessary notifications dekhinna
3. **Better UX**: Cashier lai business management notifications dekhinna
4. **Scalable**: Naya roles easily add garna sakincha

## Future Enhancements

- Email notifications by role
- SMS alerts for critical notifications
- User-specific notification preferences
- Notification sound settings by type
- Push notifications for mobile app

---

**Status**: ✅ Implemented and Tested
**Date**: March 31, 2026
**Migration**: Applied successfully
