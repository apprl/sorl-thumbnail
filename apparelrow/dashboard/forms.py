from django.forms import ModelForm
from django.core.exceptions import ValidationError
from collections import Iterable



class CutAdminForm(ModelForm):
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
                    else:
                        raise ValidationError("JSON key is not valid: %s."%(key))
        return rules_exceptions
        
