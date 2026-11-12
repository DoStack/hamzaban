from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class ClientRegistrationForm(UserCreationForm):
    first_name = forms.CharField(label="نام", max_length=150)
    email = forms.EmailField(
        label="ایمیل",
        error_messages={"invalid": "یک ایمیل معتبر وارد کنید."},
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "نام کاربری"
        self.fields["password1"].label = "گذرواژه"
        self.fields["password2"].label = "تکرار گذرواژه"
        self.fields["username"].help_text = ""
        self.fields["username"].widget.attrs.pop("autofocus", None)
        self.fields["password1"].help_text = "حداقل ۸ نویسه، و شبیه نام یا ایمیل نباشد."
        self.fields["password2"].help_text = ""
        self.fields["first_name"].widget.attrs["autocomplete"] = "given-name"
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"
        self.fields["first_name"].widget.attrs["autofocus"] = True
        self.order_fields(["first_name", "username", "email", "password1", "password2"])

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user
