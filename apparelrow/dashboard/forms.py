from django.core.exceptions import ValidationError
from collections import Iterable
from django.db.models import get_model
from django.contrib.auth import get_user_model
from django import forms


class CutAdminForm(forms.ModelForm):
    def clean_rules_exceptions(self):
        rules_exceptions = self.cleaned_data["rules_exceptions"]
        if isinstance(rules_exceptions, Iterable):
            for rule in rules_exceptions:
                for key, value in rule.items():
                    if key == "sid":
                        pass
                    elif key == "tribute":
                        if value < 0 or value > 1:
                            raise ValidationError("Value for tribute is not valid. Insert a number between 0 and 1.")
                    elif key == "cut":
                        if value < 0 or value > 1:
                            raise ValidationError("Value for cut is not valid. Insert a number between 0 and 1.")
                    elif key == "click_cost":
                        if not len(value.split(" ")) == 2:
                            raise ValidationError("Value for click is not valid. Insert amount and currency. Ex: '10 EUR'.")
                    else:
                        raise ValidationError("JSON key is not valid: %s."%(key))
        return rules_exceptions


class SaleAdminFormCustom(forms.ModelForm):

    class Meta:
        model = get_model('dashboard', 'Sale')

    def clean(self):
        user_id = self.cleaned_data['user_id']
        is_promo = self.cleaned_data['is_promo']
        if not get_user_model().objects.filter(id=user_id).exists():
            raise forms.ValidationError("User %s does not exist." % user_id)
        if is_promo:
            if get_model('dashboard', 'Sale').objects.filter(is_promo=True, user_id=user_id).count() > 0:
                raise forms.ValidationError("Referral bonus for user %s already exists." % user_id)
        return self.cleaned_data