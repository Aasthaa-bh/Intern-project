import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'POSsystem.settings')
django.setup()

from pos.models import Item
import cloudinary
import cloudinary.uploader
from core.cloudinary_utils import get_cloudinary_upload_path
from django.conf import settings

# Initialize cloudinary config which is missing in models.py
cloudinary.config(
    cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
    api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
    api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
)

item = Item.objects.exclude(image="").last()
print('Item:', item)
if item and item.image:
    print('Original URL:', item.image.url)
    
    safe_filename = os.path.basename(item.image.name)
    thumb_path = get_cloudinary_upload_path(item, safe_filename, image_type='thumbnail')
    public_id = thumb_path.rsplit('.', 1)[0]
    print('Thumb public ID:', public_id)
    
    try:
        result = cloudinary.uploader.upload(
            item.image.url,
            public_id=public_id,
            transformation=[{'width': 200, 'height': 200, 'crop': 'fill', 'quality': 'auto'}],
            overwrite=True,
            resource_type="image"
        )
        print('Upload Success!', result.get('secure_url'))
    except Exception as e:
        print('Upload Failed!', e)
