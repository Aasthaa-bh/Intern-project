from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.decorators import owner_required
from .models import Category
from .forms import CategoryForm


@owner_required
def category_list(request):
    categories = Category.objects.filter(
        business=request.user.business
    ).order_by("-created_at")

    return render(request, "owner/categories/category_list.html", {
        "categories": categories
    })


@owner_required
def category_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, business=request.user.business)
        if form.is_valid():
            category = form.save(commit=False)
            category.business = request.user.business
            category.save()
            messages.success(request, "Category created successfully.")
            return redirect("category_list")
    else:
        form = CategoryForm(business=request.user.business)

    return render(request, "owner/categories/category_form.html", {
        "form": form,
        "mode": "create"
    })


@owner_required
def category_edit(request, category_id):
    category = get_object_or_404(
        Category,
        id=category_id,
        business=request.user.business
    )

    if request.method == "POST":
        form = CategoryForm(
            request.POST,
            instance=category,
            business=request.user.business
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("category_list")
    else:
        form = CategoryForm(
            instance=category,
            business=request.user.business
        )

    return render(request, "owner/categories/category_form.html", {
        "form": form,
        "mode": "edit",
    })


@owner_required
def category_delete(request, category_id):
    category = get_object_or_404(
        Category,
        id=category_id,
        business=request.user.business
    )

    if request.method == "POST":
        category.delete()
        messages.success(request, "Category deleted successfully.")
        return redirect("category_list")

    return render(request, "owner/categories/category_delete.html", {
        "category": category
    })