from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from subscription.utils import get_business_table_limit
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
def table_category_edit(request, category_id):
    category = get_object_or_404(
        TableCategory,
        id=category_id,
        business=request.user.business
    )

    if request.method == "POST":
        form = TableCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Table category updated.")
            return redirect("table_category_list")
    else:
        form = TableCategoryForm(instance=category)

    return render(request, "owner/tables/category_form.html", {
        "form": form,
        "mode": "edit"
    })


@owner_required
def table_category_delete(request, category_id):
    category = get_object_or_404(
        TableCategory,
        id=category_id,
        business=request.user.business
    )

    if request.method == "POST":
        category.delete()
        messages.success(request, "Table category deleted.")
        return redirect("table_category_list")

    return render(request, "owner/tables/category_delete.html", {
        "category": category
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
    business = request.user.business
    max_tables = int(get_business_table_limit(business) or 0)
    current_tables = DiningTable.objects.filter(business=business).count()

    if current_tables >= max_tables:
        messages.error(
            request,
            f"Table limit reached. Your current package allows only {max_tables} tables."
        )
        return redirect("business_package_list")

    if request.method == "POST":
        form = DiningTableForm(request.POST, business=business)
        if form.is_valid():
            max_tables = int(get_business_table_limit(business) or 0)
            current_tables = DiningTable.objects.filter(business=business).count()

            if current_tables >= max_tables:
                messages.error(
                    request,
                    f"Table limit reached. Your current package allows only {max_tables} tables."
                )
                return redirect("business_package_list")

            table = form.save(commit=False)
            table.business = business
            table.name = f"{table.category.code_prefix}{table.number}"
            table.save()

            messages.success(request, "Table created successfully.")
            return redirect("table_list")
        else:
            print("FORM ERRORS:", form.errors)
    else:
        form = DiningTableForm(business=business)

    return render(request, "owner/tables/table_form.html", {
        "form": form,
        "mode": "create"
    })


@owner_required
def table_edit(request, table_id):
    table = get_object_or_404(
        DiningTable,
        id=table_id,
        business=request.user.business
    )

    if request.method == "POST":
        form = DiningTableForm(
            request.POST,
            instance=table,
            business=request.user.business
        )
        if form.is_valid():
            table = form.save(commit=False)
            table.name = f"{table.category.code_prefix}{table.number}"
            table.save()

            messages.success(request, "Table updated successfully.")
            return redirect("table_list")
        else:
            print("FORM ERRORS:", form.errors)
    else:
        form = DiningTableForm(instance=table, business=request.user.business)

    return render(request, "owner/tables/table_form.html", {
        "form": form,
        "mode": "edit"
    })


@owner_required
def table_delete(request, table_id):
    table = get_object_or_404(
        DiningTable,
        id=table_id,
        business=request.user.business
    )

    if request.method == "POST":
        table.delete()
        messages.success(request, "Table deleted successfully.")
        return redirect("table_list")

    return render(request, "owner/tables/table_delete.html", {
        "table": table
    })