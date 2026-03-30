import os

def get_business_type_code(user):
    if not user or not getattr(user, "business", None) or not user.business.business_type:
        return None

    return user.business.business_type.name.strip().lower()

def generate_thumbnail_for_field(instance, image_field_name, thumb_field_name):
    """
    Helper to generate a thumbnail for a given ImageField on an instance.
    Uses Pillow to create a lightweight JPEG version.
    """
    image_field = getattr(instance, image_field_name)
    
    # Check if the image changed
    image_changed = False
    if instance.pk:
        try:
            old = instance.__class__.objects.get(pk=instance.pk)
            # Compare current field's name/object with the old one
            image_changed = getattr(old, image_field_name) != image_field
        except Exception:
            pass
    else:
        if image_field:
            image_changed = True

    if image_changed and image_field:
        from io import BytesIO
        from PIL import Image as PilImage
        from django.core.files.uploadedfile import InMemoryUploadedFile
        import sys

        try:
            # We must open directly from the field
            img = PilImage.open(image_field)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # Reset file pointer just in case
            image_field.seek(0)

            # Create a lightweight thumbnail version
            img.thumbnail((400, 400))
            thumb_io = BytesIO()
            img.save(thumb_io, format='JPEG', quality=60)
            
            # Reset file pointer for the new IO
            thumb_io.seek(0)

            # Extract a reasonable filename
            raw_filename = str(getattr(image_field, 'name', 'image.jpg') or 'image.jpg')
            filename = os.path.basename(raw_filename)
            name_without_ext = filename.rsplit('.', 1)[0]
            thumb_filename = f"{name_without_ext}_thumb.jpg"

            # Create the Django file object
            # Use getbuffer().nbytes for accurate size reporting
            size = thumb_io.getbuffer().nbytes
            thumbnail_file = InMemoryUploadedFile(
                thumb_io,
                'ImageField',
                thumb_filename,
                'image/jpeg',
                size,
                None
            )
            # Set it back onto the instance
            setattr(instance, thumb_field_name, thumbnail_file)
        except Exception as e:
            # Silence image processing errors
            print(f"Thumbnail error: {e}")
            pass

import os