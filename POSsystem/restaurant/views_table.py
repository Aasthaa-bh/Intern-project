from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from core.decorators import owner_required
from .models import TableCategory, DiningTable
from .forms import DiningTableForm, TableCategoryForm


@owner_required
def table_category_list(request):
    categories = TableCategory.objects.filter(
        business=request.user.business
    )

    return render(request, "owner/tables/category_list.html", {
        "categories": categories
    })


@owner_required
def table_category_create(request):
    if request.method == "POST":
        form = TableCategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.business = request.user.business
            category.save()
            messages.success(request, "Table category created.")
            return redirect("table_category_list")
    else:
        form = TableCategoryForm()

    return render(request, "owner/tables/category_form.html", {
        "form": form,
        "mode": "create"
    })
    
@owner_required
def table_list(request):
    tables = DiningTable.objects.filter(
        business=request.user.business
    ).order_by("name")

    return render(request, "owner/tables/table_list.html", {
        "tables": tables
    })


@owner_required
def table_create(request):
    if request.method == "POST":
        form = DiningTableForm(request.POST, business=request.user.business)
        if form.is_valid():
            table = form.save(commit=False)
            table.business = request.user.business
            table.save()
            messages.success(request, "Table created successfully.")
            return redirect("table_list")
    else:
        form = DiningTableForm(business=request.user.business)

    return render(request, "owner/tables/table_form.html", {
        "form": form,
        "mode": "create"
    })