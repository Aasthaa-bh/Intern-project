from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.decorators import owner_required
from .models import Item
from .forms import ItemForm


@owner_required
def item_list(request):
    items = Item.objects.filter(
        business=request.user.business
    ).order_by("-created_at")

    return render(request, "owner/items/item_list.html", {
        "items": items
    })


@owner_required
def item_create(request):
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, business=request.user.business)
        if form.is_valid():
            item = form.save(commit=False)
            item.business = request.user.business
            item.item_type = "MENU"   # 🔥 force as MENU
            item.save()
            
            messages.success(request, "Item created successfully.")
            return redirect("item_list")
    else:
        form = ItemForm(business=request.user.business)

    return render(request, "owner/items/item_form.html", {
        "form": form,
        "mode": "create"
    })


@owner_required
def item_edit(request, item_id):
    item = get_object_or_404(
        Item,
        id=item_id,
        business=request.user.business
    )

    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item, business=request.user.business)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated successfully.")
            return redirect("item_list")
    else:
        form = ItemForm(instance=item, business=request.user.business)

    return render(request, "owner/items/item_form.html", {
        "form": form,
        "mode": "edit"
    })
    
@owner_required
def item_delete(request, item_id):
    item = get_object_or_404(
        Item,
        id=item_id,
        business=request.user.business
    )

    if request.method == "POST":
        item.delete()
        messages.success(request, "Item deleted successfully.")
        return redirect("item_list")

    return render(request, "owner/items/item_delete.html", {
        "item": item
    })