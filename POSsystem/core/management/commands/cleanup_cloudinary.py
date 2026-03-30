"""
Management command: cleanup_cloudinary
---------------------------------------
Step 1: Finds ALL old Cloudinary image paths stored in Railway DB.
Step 2: Deletes each image from Cloudinary.
Step 3: Clears the path from the DB column (sets it to blank/null).

After running this, all new uploads will use the clean new path:
  POS/Business/{id}/{AppType}/{original|thumbnail}/{filename}

Usage:
    python manage.py cleanup_cloudinary
    python manage.py cleanup_cloudinary --dry-run   (just show, don't delete)
"""

import cloudinary
import cloudinary.uploader

from django.core.management.base import BaseCommand
from django.conf import settings

from core.models import BusinessRequest
from pos.models import Item
from subscription.models import SubscriptionPayment


class Command(BaseCommand):
    help = "Delete all old Cloudinary images and clear their paths from the Railway DB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Configure Cloudinary from Django settings
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_STORAGE["CLOUD_NAME"],
            api_key=settings.CLOUDINARY_STORAGE["API_KEY"],
            api_secret=settings.CLOUDINARY_STORAGE["API_SECRET"],
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN — nothing will be deleted ===\n"))

        total_deleted = 0
        total_errors = 0

        # ──────────────────────────────────────────
        # TABLE 1: pos_item  (image + thumbnail)
        # ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n[1/3] Cleaning pos_item (product images)..."))

        items_with_images = Item.objects.exclude(image="").exclude(image__isnull=True)
        for item in items_with_images:
            deleted, err = self._delete_from_cloudinary(item.image.name, dry_run)
            if deleted:
                total_deleted += 1
            if err:
                total_errors += 1

        items_with_thumbs = Item.objects.exclude(thumbnail="").exclude(thumbnail__isnull=True)
        for item in items_with_thumbs:
            deleted, err = self._delete_from_cloudinary(item.thumbnail.name, dry_run)
            if deleted:
                total_deleted += 1
            if err:
                total_errors += 1

        if not dry_run:
            Item.objects.exclude(image="").exclude(image__isnull=True).update(image="")
            Item.objects.exclude(thumbnail="").exclude(thumbnail__isnull=True).update(thumbnail="")
            self.stdout.write(self.style.SUCCESS("  ✓ Cleared image & thumbnail columns in pos_item"))

        # ──────────────────────────────────────────
        # TABLE 2: core_businessrequest  (pan + citizenship)
        # ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n[2/3] Cleaning core_businessrequest (documents)..."))

        for br in BusinessRequest.objects.all():
            if br.pan_image:
                deleted, err = self._delete_from_cloudinary(br.pan_image.name, dry_run)
                if deleted:
                    total_deleted += 1
                if err:
                    total_errors += 1
            if br.citizenship_image:
                deleted, err = self._delete_from_cloudinary(br.citizenship_image.name, dry_run)
                if deleted:
                    total_deleted += 1
                if err:
                    total_errors += 1

        # NOTE: pan_image and citizenship_image are required fields (no blank=True)
        # so we cannot set them to empty — we leave DB rows as-is.
        # They will be overwritten when re-uploaded.
        self.stdout.write(self.style.WARNING(
            "  ⚠ pan_image & citizenship_image are required fields — "
            "DB paths kept, images deleted from Cloudinary. Re-upload to fix."
        ))

        # ──────────────────────────────────────────
        # TABLE 3: subscription_subscriptionpayment  (payment_proof)
        # ──────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n[3/3] Cleaning subscription_subscriptionpayment (payment proofs)..."))

        for payment in SubscriptionPayment.objects.exclude(payment_proof="").exclude(payment_proof__isnull=True):
            deleted, err = self._delete_from_cloudinary(payment.payment_proof.name, dry_run)
            if deleted:
                total_deleted += 1
            if err:
                total_errors += 1

        if not dry_run:
            SubscriptionPayment.objects.exclude(payment_proof="").exclude(payment_proof__isnull=True).update(payment_proof="")
            self.stdout.write(self.style.SUCCESS("  ✓ Cleared payment_proof column in subscription_subscriptionpayment"))

        # ──────────────────────────────────────────
        # SUMMARY
        # ──────────────────────────────────────────
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"  ✅ Images deleted from Cloudinary : {total_deleted}"))
        if total_errors:
            self.stdout.write(self.style.ERROR(f"  ❌ Errors (already gone or bad path): {total_errors}"))
        self.stdout.write(self.style.SUCCESS(
            "\n  New uploads will now use the clean path:\n"
            "  POS/Business/{id}/{AppType}/{original|thumbnail}/{filename}"
        ))

    def _delete_from_cloudinary(self, path, dry_run):
        """
        Delete a single file from Cloudinary by its stored path.
        Returns (deleted: bool, error: bool)
        """
        if not path:
            return False, False

        # Cloudinary public_id is the path WITHOUT the file extension
        public_id = path.rsplit(".", 1)[0]

        self.stdout.write(f"  → {'[DRY RUN] Would delete' if dry_run else 'Deleting'}: {public_id}")

        if dry_run:
            return True, False

        try:
            result = cloudinary.uploader.destroy(public_id, invalidate=True)
            if result.get("result") == "ok":
                self.stdout.write(self.style.SUCCESS(f"    ✓ Deleted"))
                return True, False
            else:
                # "not found" means it was already gone — not a real error
                self.stdout.write(self.style.WARNING(f"    ⚠ Cloudinary response: {result.get('result')} (may already be deleted)"))
                return False, True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"    ✗ Error: {e}"))
            return False, True
