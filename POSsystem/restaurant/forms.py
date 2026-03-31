from django import forms
from subscription.utils import get_business_table_limit
from .models import TableCategory, DiningTable


class TableCategoryForm(forms.ModelForm):
    class Meta:
        model = TableCategory
        fields = ["name", "code_prefix"]


class DiningTableForm(forms.ModelForm):
    class Meta:
        model = DiningTable
        fields = ["category", "number", "capacity", "status"]

    def __init__(self, *args, **kwargs):
        self.business = kwargs.pop("business", None)
        super().__init__(*args, **kwargs)

        if self.business:
            self.fields["category"].queryset = TableCategory.objects.filter(
                business=self.business
            )

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        number = cleaned_data.get("number")

        if self.business and not self.instance.pk:
            max_tables = int(get_business_table_limit(self.business) or 0)
            current_tables = DiningTable.objects.filter(
                business=self.business
            ).count()

            if current_tables >= max_tables:
                raise forms.ValidationError(
                    f"Table limit reached. Your current package allows only {max_tables} tables."
                )

        if category and number and self.business:
            generated_name = f"{category.code_prefix}{number}"

            qs = DiningTable.objects.filter(
                business=self.business,
                name=generated_name
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    f"Table '{generated_name}' already exists."
                )


from .models import RestaurantNotification

# RestaurantNotificationForm
class RestaurantNotificationForm(forms.ModelForm):
    class Meta:
        model = RestaurantNotification
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "class": "form-control", "placeholder": "Enter notification message..."}),
        }
