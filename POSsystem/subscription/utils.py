from subscription.models import BusinessSubscription

def get_active_subscription(business):
    return BusinessSubscription.objects.filter(
        business=business,
        status="ACTIVE",
        is_current=True
    ).select_related("package").first()


def get_business_user_limit(business):
    sub = get_active_subscription(business)
    if not sub:
        return 3
    return sub.package.max_users