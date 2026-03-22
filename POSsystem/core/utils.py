def get_business_type_code(user):
    if not user or not getattr(user, "business", None) or not user.business.business_type:
        return None

    return user.business.business_type.name.strip().lower()