# 📍 Notification Code Locations

## 1️⃣ PRODUCT ADD NOTIFICATION

**File:** `POSsystem/clothing/views.py`
**Function:** `product_create()`
**Line:** Around 680-695

```python
# Create notifications for product creation
from .models import Notification

# Notification for Admin
Notification.objects.create(
    business=business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='New Product Added',
    message=f'Product "{product.name}" has been added to inventory.',
    link=f'/clothing/products/{product.id}/',
    is_read=False
)

# Notification for Cashier (so they know new product is available)
Notification.objects.create(
    business=business,
    notification_type='GENERAL',
    target_role='CASHIER',
    title='New Product Available',
    message=f'New product "{product.name}" is now available for sale.',
    link='',
    is_read=False
)
```

---

## 2️⃣ PAYMENT SUCCESS NOTIFICATION

**File:** `POSsystem/clothing/esewa.py`
**Function:** `esewa_success()`
**Line:** Around 280-305

```python
# Create notifications for successful payment
from clothing.models import Notification
business = ep.business

if business:
    # Notification for Admin
    Notification.objects.create(
        business=business,
        notification_type='PAYMENT_COMPLETED',
        target_role='ADMIN',
        title='Payment Completed',
        message=f'eSewa payment successful. Amount: Rs {ep.amount}. Order: {order.order_no}',
        link='',
        is_read=False
    )
    
    # Notification for Cashier
    Notification.objects.create(
        business=business,
        notification_type='PAYMENT_COMPLETED',
        target_role='CASHIER',
        title='Payment Successful',
        message=f'Customer payment completed via eSewa. Amount: Rs {ep.amount}. Order: {order.order_no}',
        link='',
        is_read=False
    )
```

---

## 3️⃣ PAYMENT CANCEL/FAILURE NOTIFICATION

**File:** `POSsystem/clothing/esewa.py`
**Function:** `esewa_failure()`
**Line:** Around 310-380

```python
# Case 1: With transaction UUID
if txn_uuid:
    # ... payment update code ...
    
    # Create notifications for payment failure
    from clothing.models import Notification
    
    if business:
        # Notification for Admin
        Notification.objects.create(
            business=business,
            notification_type='PAYMENT_FAILED',
            target_role='ADMIN',
            title='Payment Failed',
            message=f'Payment cancelled or failed. Amount: Rs {ep.amount}. Transaction: {txn_uuid}',
            link='',
            is_read=False
        )
        
        # Notification for Cashier
        Notification.objects.create(
            business=business,
            notification_type='PAYMENT_FAILED',
            target_role='CASHIER',
            title='Payment Cancelled',
            message=f'Customer payment was cancelled or failed. Amount: Rs {ep.amount}. Transaction: {txn_uuid}',
            link='',
            is_read=False
        )

# Case 2: Without transaction UUID (user cancelled early)
else:
    if business:
        from clothing.models import Notification
        
        # ... find recent pending payment ...
        
        # Create notifications even without specific transaction
        Notification.objects.create(
            business=business,
            notification_type='PAYMENT_FAILED',
            target_role='ADMIN',
            title='Payment Cancelled',
            message=f'A payment was cancelled by cashier {request.user.username}.',
            link='',
            is_read=False
        )
        
        Notification.objects.create(
            business=business,
            notification_type='PAYMENT_FAILED',
            target_role='CASHIER',
            title='Payment Cancelled',
            message='Payment was cancelled before completion.',
            link='',
            is_read=False
        )
```

---

## 4️⃣ SUPPLIER ADD NOTIFICATION

**File:** `POSsystem/clothing/views.py`
**Function:** `supplier_create()`
**Line:** Around 1650-1665

```python
# Create notification for supplier creation
from clothing.models import Notification
Notification.objects.create(
    business=business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='New Supplier Added',
    message=f'Supplier "{supplier.name}" has been added to the system.',
    link='/clothing/suppliers/',
    is_read=False
)
```

---

## 5️⃣ SUPPLIER UPDATE NOTIFICATION

**File:** `POSsystem/clothing/views.py`
**Function:** `supplier_edit()`
**Line:** Around 1695-1710

```python
# Create notification for supplier update
from clothing.models import Notification
Notification.objects.create(
    business=business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='Supplier Updated',
    message=f'Supplier "{supplier.name}" information has been updated.',
    link='/clothing/suppliers/',
    is_read=False
)
```

---

## 6️⃣ SUPPLIER ARCHIVE NOTIFICATION

**File:** `POSsystem/clothing/views.py`
**Function:** `supplier_delete()`
**Line:** Around 1740-1755

```python
# Create notification for supplier archive
from clothing.models import Notification
Notification.objects.create(
    business=business,
    notification_type='GENERAL',
    target_role='ADMIN',
    title='Supplier Archived',
    message=f'Supplier "{supplier_name}" has been archived (used in purchases).',
    link='/clothing/suppliers/',
    is_read=False
)
```

---

## 7️⃣ NOTIFICATION DISPLAY (Context Processor)

**File:** `POSsystem/core/context_processors.py`
**Function:** `notifications()`
**Line:** Full file

```python
def notifications(request):
    """Add notifications and business context to all pages"""
    # ... authentication checks ...
    
    if business_type == 'clothing':
        from clothing.models import Notification
        from django.db.models import Q
        
        # Determine user role for notification filtering
        user_role = request.user.role
        
        # Map user roles to notification target roles
        if user_role in ['SUPERADMIN', 'OWNER']:
            # Admin users see ADMIN and ALL notifications
            role_filter = Q(target_role='ADMIN') | Q(target_role='ALL')
        elif user_role == 'CASHIER':
            # Cashiers see CASHIER and ALL notifications
            role_filter = Q(target_role='CASHIER') | Q(target_role='ALL')
        else:
            # Other roles see only ALL notifications
            role_filter = Q(target_role='ALL')
        
        # Get notifications from last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        all_recent = Notification.objects.filter(
            business=business,
            created_at__gte=thirty_days_ago
        ).filter(role_filter).order_by('-created_at')
        
        # Count unread before slicing
        unread_count = all_recent.filter(is_read=False).count()
        
        # Get top 3 for display
        recent_notifications = list(all_recent[:3])
```

---

## 8️⃣ NOTIFICATION MODEL

**File:** `POSsystem/clothing/models.py`
**Model:** `Notification`

```python
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('LOW_STOCK', 'Low Stock'),
        ('OFFER_CREATED', 'Offer Created'),
        ('OFFER_EXPIRING', 'Offer Expiring'),
        ('PURCHASE_RECEIVED', 'Purchase Received'),
        ('PAYMENT_COMPLETED', 'Payment Completed'),
        ('PAYMENT_FAILED', 'Payment Failed'),
        ('GENERAL', 'General'),
    ]
    
    TARGET_ROLES = [
        ('ADMIN', 'Admin'),
        ('CASHIER', 'Cashier'),
        ('ALL', 'All'),
    ]
    
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    target_role = models.CharField(max_length=20, choices=TARGET_ROLES, default='ADMIN')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 📋 Summary - Notification Code Locations

| Notification Type | File | Function | Target Role |
|------------------|------|----------|-------------|
| Product Add | `clothing/views.py` | `product_create()` | Admin + Cashier |
| Payment Success | `clothing/esewa.py` | `esewa_success()` | Admin + Cashier |
| Payment Cancel | `clothing/esewa.py` | `esewa_failure()` | Admin + Cashier |
| Supplier Add | `clothing/views.py` | `supplier_create()` | Admin only |
| Supplier Update | `clothing/views.py` | `supplier_edit()` | Admin only |
| Supplier Archive | `clothing/views.py` | `supplier_delete()` | Admin only |
| Low Stock | `clothing/management/commands/check_low_stock.py` | Command | Admin only |
| Offer Created | `clothing/views_offer.py` | Offer views | Admin only |
| Offer Expiring | `clothing/management/commands/check_expiring_offers.py` | Command | Admin only |

---

## 🔧 Configuration Files

1. **Context Processor Registration**
   - File: `POSsystem/POSsystem/settings.py`
   - Location: `TEMPLATES[0]['OPTIONS']['context_processors']`
   - Entry: `'core.context_processors.notifications'`

2. **Notification Display**
   - File: `POSsystem/templates/owner/base.html`
   - Location: Bell icon dropdown in navbar

---

## ✅ All Notification Codes Ready!

Sabai notification codes implement bhaisakyo:
- ✅ Product add → Admin + Cashier
- ✅ Payment success → Admin + Cashier
- ✅ Payment cancel → Admin + Cashier
- ✅ Supplier add/edit/delete → Admin only
- ✅ Low stock → Admin only
- ✅ Offers → Admin only

Server restart गरेर test गर्नुहोस्! 🚀
