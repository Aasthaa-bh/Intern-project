from sys import prefix

from django.db import models
from django.conf import settings
# import random
# import string
# from django.core.mail import send_mail
# from django.utils import timezone
# from accounts.models import User

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

    pan_image = models.ImageField(upload_to="documents/pan/")
    citizenship_image = models.ImageField(upload_to="documents/citizenship/")

    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


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