from django import forms


class TransactionForm(forms.Form):
    amount = forms.IntegerField(min_value=0)
    reference_id = forms.UUIDField()
