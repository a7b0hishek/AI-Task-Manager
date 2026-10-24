from django import forms

from GenAI_app.models import Task


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = (
            'name',
            'description',
            'original_budget',
            'spent_budget',
            'starting_date',
            'deadline_date',
            'recommendation',
        )
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. Launch marketing campaign'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'What needs to be completed?'}),
            'original_budget': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01', 'placeholder': 'e.g. 20000'}),
            'spent_budget': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'starting_date': forms.DateInput(attrs={'type': 'date'}),
            'deadline_date': forms.DateInput(attrs={'type': 'date'}),
            'recommendation': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Add an initial recommendation'}),
        }

    def clean_original_budget(self):
        value = self.cleaned_data['original_budget']
        if value <= 0:
            raise forms.ValidationError('Original budget must be greater than zero.')
        return value

    def clean_spent_budget(self):
        value = self.cleaned_data['spent_budget']
        if value < 0:
            raise forms.ValidationError('Spent budget cannot be negative.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        starting_date = cleaned_data.get('starting_date')
        deadline_date = cleaned_data.get('deadline_date')
        if starting_date and deadline_date and deadline_date < starting_date:
            raise forms.ValidationError('Deadline date cannot be before the starting date.')
        return cleaned_data


class TaskUpdateForm(forms.ModelForm):
    task_number = forms.IntegerField(min_value=1)
    generate_recommendation = forms.BooleanField(required=False)

    class Meta:
        model = Task
        fields = ('task_number', 'spent_budget', 'recommendation')
        widgets = {
            'spent_budget': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'placeholder': 'Leave unchanged'}),
            'recommendation': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Enter the recommendation to show on the dashboard'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['spent_budget'].required = False
        self.fields['recommendation'].required = False

    def clean_spent_budget(self):
        value = self.cleaned_data['spent_budget']
        if value is not None and value < 0:
            raise forms.ValidationError('Spent budget cannot be negative.')
        return value
