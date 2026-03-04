from django import forms
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

        if category and number and self.business:
            generated_name = f"{category.code_prefix}{number}"

            # Exclude current instance (for edit case)
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

        return cleaned_data