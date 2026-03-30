import os

def get_cloudinary_upload_path(instance, filename, image_type='original'):
    """
    Generates a Cloudinary path based on the instance and filename.
    Clean Structure: POS/Business/{business_id}/{AppType}/{original|thumbnail}/{filename}
    Example: POS/Business/3/Clothing/original/shirt.jpg
    """
    # Clean root — no redundant folders
    root_path = "POS/Business"
    
    # Identify Business ID or User ID (based on what's available)
    # The diagram says "Business -> Id or userId"
    identifier = "unknown"
    
    # Try to find a business id first
    if hasattr(instance, 'business') and instance.business and instance.business.id:
        identifier = str(instance.business.id)
    elif hasattr(instance, 'id') and hasattr(instance, 'business_name'): # Likely Business model
        identifier = str(instance.id)
    elif hasattr(instance, 'user') and instance.user and instance.user.business:
        identifier = str(instance.user.business.id)
    elif hasattr(instance, 'created_by') and instance.created_by and getattr(instance.created_by, 'business', None):
        identifier = str(instance.created_by.business.id)
    # If no business ID, rollback to User ID
    elif hasattr(instance, 'user') and instance.user and instance.user.id:
        identifier = str(instance.user.id)
    elif hasattr(instance, 'created_by') and instance.created_by and instance.created_by.id:
        identifier = str(instance.created_by.id)
    elif hasattr(instance, 'reviewed_by') and instance.reviewed_by and instance.reviewed_by.id:
        identifier = str(instance.reviewed_by.id)
    elif hasattr(instance, 'email'): # Likely BusinessRequest
        identifier = "request_pending"

    # Determine App Type (Restaurant, Mart, Clothing)
    app_type = "POS"
    
    # Try to get it from BusinessType
    b_type = None
    if hasattr(instance, 'business') and instance.business and instance.business.business_type:
        b_type = instance.business.business_type.name
    elif hasattr(instance, 'business_type') and instance.business_type:
        b_type = instance.business_type.name
    
    if b_type:
        b_type_lower = b_type.lower()
        if any(keyword in b_type_lower for keyword in ["rest", "food", "cafe"]):
            app_type = "Restaurant"
        elif any(keyword in b_type_lower for keyword in ["cloth", "garment", "fashion"]):
            app_type = "Clothing"
        elif any(keyword in b_type_lower for keyword in ["mart", "shop", "grocery"]):
            app_type = "Mart"
        else:
            app_type = b_type.capitalize()

    # Image Type Folder
    type_folder = "thumbnail" if image_type == "thumbnail" else "original"

    # Final Path Construction
    # 1. Special Case: BusinessRequest (PAN, Citizenship) - Undo to afternoon logic
    if hasattr(instance, 'owner_name') and hasattr(instance, 'email'):
        request_root = "POS/Business-Request"
        b_name = str(getattr(instance, "business_name", "unknown") or "unknown")
        safe_type_folder = "thumbnail" if image_type == "thumbnail" else "original"
        safe_filename = str(filename or "image.jpg")
        return f"{request_root}/{b_name}/{safe_type_folder}/{safe_filename}"

    # 2. Standard Case: Clothing, Mart, Restaurant (Approved Business and Products)
    safe_identifier = str(identifier or "unknown")
    safe_app_type = str(app_type or "POS")
    safe_type_folder = str(type_folder or "original")
    safe_filename = str(filename or "image.jpg")

    # We combine them into the structure: root/identifier/app_type/type_folder/filename
    return f"{root_path}/{safe_identifier}/{safe_app_type}/{safe_type_folder}/{safe_filename}"
