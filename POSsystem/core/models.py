import os
from django.db import models
from django.conf import settings
import cloudinary.uploader
from .cloudinary_utils import get_cloudinary_upload_path

def cloudinary_original_path(instance, filename):
    return get_cloudinary_upload_path(instance, filename, image_type='original')

def cloudinary_thumbnail_path(instance, filename):
    return get_cloudinary_upload_path(instance, filename, image_type='thumbnail')

cloudinary_document_path = cloudinary_original_path
cloudinary_document_thumbnail_path = cloudinary_thumbnail_path

class BusinessType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    code=models.CharField(max_length=20, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Business(models.Model):
    business_type = models.ForeignKey(BusinessType, on_delete=models.PROTECT)
    business_name = models.CharField(max_length=255)
    business_code = models.CharField(max_length=20, unique=True)
    address = models.TextField()
    status = models.CharField(max_length=20, default="ACTIVE")
    pan_image = models.ImageField(upload_to=cloudinary_original_path, max_length=512, null=True, blank=True)
    citizenship_image = models.ImageField(upload_to=cloudinary_original_path, max_length=512, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Determine which images are entirely new uploads
        new_images = []
        for field_name in ['pan_image', 'citizenship_image']:
            f = getattr(self, field_name)
            if f and (not hasattr(f, 'name') or not f.name):
                f.name = 'image.jpg'
                
            if f:
                if not self.pk:
                    new_images.append(field_name)
                else:
                    try:
                        old = Business.objects.get(pk=self.pk)
                        old_f = getattr(old, field_name)
                        if not old_f or old_f.name != f.name:
                            new_images.append(field_name)
                    except Business.DoesNotExist:
                        new_images.append(field_name)

        super().save(*args, **kwargs)

        # Physical Thumbnail Upload logic via robust CDN URLs
        if new_images:
            try:
                from django.conf import settings
                import cloudinary.uploader
                
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                    api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
                    api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
                )
                
                for field_name in new_images:
                    image_field = getattr(self, field_name)
                    if image_field and hasattr(image_field, 'url'):
                        safe_filename = os.path.basename(image_field.name)
                        thumb_path = get_cloudinary_upload_path(self, safe_filename, image_type='thumbnail')
                        
                        media_prefix = getattr(settings, 'MEDIA_URL', '/media/').strip('/')
                        if media_prefix:
                            thumb_path = f"{media_prefix}/{thumb_path}"
                            
                        public_id = thumb_path.rsplit('.', 1)[0]
                        folder_path = os.path.dirname(public_id)
                        filename_only = os.path.basename(public_id)
                        
                        # Upload tightly integrated into folder structure
                        cloudinary.uploader.upload(
                            image_field.url,
                            public_id=filename_only,
                            folder=folder_path,
                            transformation=[{'width': 400, 'height': 400, 'crop': 'fill', 'quality': 'auto'}],
                            overwrite=True,
                            resource_type="image"
                        )
            except Exception as e:
                print(f"Cloudinary document thumbnail upload error: {e}")

    @property
    def pan_thumbnail(self):
        if self.pan_image:
            # Predictable physical path for the thumbnail
            return self.pan_image.url.replace('/original/', '/thumbnail/')
        return驱动None

    @property
    def citizenship_thumbnail(self):
        if self.citizenship_image:
            return self.citizenship_image.url.replace('/original/', '/thumbnail/')
        return None

    @property
    def type_name(self):
        if self.business_type_id and self.business_type:
            return (self.business_type.name or "").strip().lower()
        return ""

    @property
    def is_clothing_business(self):
        type_name = self.type_name
        return any(keyword in type_name for keyword in ["cloth", "garment", "fashion", "apparel"])

    def __str__(self):
        return self.business_name


class BusinessRequest(models.Model):

    STATUS = (
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    business_name = models.CharField(max_length=255)
    owner_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_no = models.CharField(max_length=20)
    business_type = models.ForeignKey(BusinessType, on_delete=models.PROTECT)
    address = models.TextField()
    pan_image = models.ImageField(upload_to=cloudinary_original_path, max_length=512, null=True, blank=True)
    citizenship_image = models.ImageField(upload_to=cloudinary_original_path, max_length=512, null=True, blank=True)


    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Determine which images are entirely new uploads
        new_images = []
        for field_name in ['pan_image', 'citizenship_image']:
            f = getattr(self, field_name)
            if f and (not hasattr(f, 'name') or not f.name):
                f.name = 'image.jpg'
                
            if f:
                if not self.pk:
                    new_images.append(field_name)
                else:
                    try:
                        old = BusinessRequest.objects.get(pk=self.pk)
                        old_f = getattr(old, field_name)
                        if not old_f or old_f.name != f.name:
                            new_images.append(field_name)
                    except BusinessRequest.DoesNotExist:
                        new_images.append(field_name)

        super().save(*args, **kwargs)

        # Physical Thumbnail Upload logic
        if new_images:
            try:
                from django.conf import settings
                import cloudinary.uploader
                
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
                    api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
                    api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
                )
                
                for field_name in new_images:
                    image_field = getattr(self, field_name)
                    if image_field and hasattr(image_field, 'url'):
                        safe_filename = os.path.basename(image_field.name)
                        thumb_path = get_cloudinary_upload_path(self, safe_filename, image_type='thumbnail')
                        
                        media_prefix = getattr(settings, 'MEDIA_URL', '/media/').strip('/')
                        if media_prefix:
                            thumb_path = f"{media_prefix}/{thumb_path}"
                            
                        public_id = thumb_path.rsplit('.', 1)[0]
                        folder_path = os.path.dirname(public_id)
                        filename_only = os.path.basename(public_id)
                        
                        cloudinary.uploader.upload(
                            image_field.url,
                            public_id=filename_only,
                            folder=folder_path,
                            transformation=[{'width': 400, 'height': 400, 'crop': 'fill', 'quality': 'auto'}],
                            overwrite=True,
                            resource_type="image"
                        )
            except Exception as e:
                print(f"Cloudinary document thumbnail upload error: {e}")

    @property
    def pan_thumbnail(self):
        if self.pan_image:
            # Predictable physical path for the thumbnail
            return self.pan_image.url.replace('/original/', '/thumbnail/')
        return None

    @property
    def citizenship_thumbnail(self):
        if self.citizenship_image:
            return self.citizenship_image.url.replace('/original/', '/thumbnail/')
        return None


    # def approve(self, superadmin_user):

    #     if self.status == "APPROVED":
    #         return


    #     # 1create business code
    #     prefix = (self.business_type.code or "BUS").upper()
    #     code = f"{prefix}{self.id:03d}"

    #     # 2create Business
    #     business = Business.objects.create(
    #         business_type=self.business_type,
    #         business_name=self.business_name,
    #         address=self.address,
    #         business_code=code,
    #         status="ACTIVE"
    #     )

    #     # 3️⃣ generate temp password
    #     temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    #     # 4️⃣ create owner user
    #     username = self.owner_name.replace(" ", "").lower()

    #     user = User.objects.create_user(
    #         username=username,
    #         password=temp_password,
    #         role="OWNER",
    #         business=business,
    #         full_name=self.owner_name,
    #         email=self.email,
    #         is_first_login=True
    #     )

    #     # 5️⃣ send email
    #     send_mail(
    #         subject="Your FlexiPOS Account Approved",
    #         message=f"""
    # Your business has been approved!

    # Business Code: {code}
    # Username: {username}
    # Password: {temp_password}

    # Login and change password immediately.
    # """,
    #         from_email=settings.DEFAULT_FROM_EMAIL,
    #         recipient_list=[self.email],
    #         fail_silently=False,
    #     )

    #     # 6️⃣ mark approved
    #     self.status = "APPROVED"
    #     self.reviewed_by = superadmin_user
    #     self.reviewed_at = timezone.now()
    #     self.save()