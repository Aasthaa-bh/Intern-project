from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.decorators import owner_required
from .models import Category, Item
from .forms import ItemForm
import cloudinary.uploader
from .models import Item


@owner_required
def item_list(request):
    items = Item.objects.filter(business=request.user.business).order_by("-created_at")

    return render(request, "owner/items/item_list.html", {"items": items})


@owner_required
def item_create(request):
    if request.method == "POST":
        form = ItemForm(request.POST, business=request.user.business)
        if form.is_valid():
            item = form.save(commit=False)
            item.business = request.user.business
            item.item_type = "MENU"  #  force as MENU
            item.save()

            messages.success(request, "Item created successfully.")
            return redirect("item_list")
    else:
        form = ItemForm(business=request.user.business)

    return render(
        request, "owner/items/item_form.html", {"form": form, "mode": "create"}
    )


@owner_required
def item_edit(request, item_id):
    item = get_object_or_404(Item, id=item_id, business=request.user.business)

    if request.method == "POST":
        form = ItemForm(request.POST, instance=item, business=request.user.business)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully.")
            return redirect("item_list")
    else:
        form = ItemForm(instance=item, business=request.user.business)

    return render(request, "owner/items/item_form.html", {"form": form, "mode": "edit"})


@owner_required
def item_delete(request, item_id):
    item = get_object_or_404(Item, id=item_id, business=request.user.business)

    if request.method == "POST":
        item.delete()
        messages.success(request, "Item deleted successfully.")
        return redirect("item_list")

    return render(request, "owner/items/item_delete.html", {"item": item})


# Antim added
def add_item(request):
    business = request.user.business
    categories = Category.objects.filter(business=business)

    if request.method == "POST":
        name = request.POST.get("name")
        price = request.POST.get("price")
        category_id = request.POST.get("category")
        item_type = request.POST.get("item_type")
        description = request.POST.get("description", "")
        image_file = request.FILES.get("image")

        image = None
        if image_file:
            result = cloudinary.uploader.upload(image_file)
            image = result["secure_url"]

        Item.objects.create(
            business=business,  #  fixes your IntegrityError
            name=name,
            price=price,
            category_id=category_id,
            item_type=item_type,
            description=description,
            image=image,
        )
        return redirect("item_list")  # change to your actual list url name

    return render(request, "pos/add_item.html", {"categories": categories})
