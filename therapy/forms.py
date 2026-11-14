import re
from pathlib import Path

from django import forms
from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from clients.forms import THERAPIST_GROUP_NAME, ClientRegistrationForm
from therapy.calendar import grid_starts, parse_jalali_date
from therapy.choices import (
    APPROACHES,
    CURRENCIES,
    EDUCATION_CHOICES,
    LANGUAGE_CHOICES,
    LICENSE_TYPES,
    MAX_UPLOAD_BYTES,
    PHOTO_EXTENSIONS,
    SPECIALTY_CHOICES,
    TIMEZONES,
    UPLOAD_EXTENSIONS,
    GENDERS,
)
from therapy.models import ClientRecord, TherapistProfile
from therapy.services import unique_slug


def clean_upload(upload, allowed):
    if not upload:
        return upload
    if upload.size > MAX_UPLOAD_BYTES:
        raise forms.ValidationError("حجم فایل باید کمتر از ۵ مگابایت باشد.")
    if Path(upload.name).suffix.lower() not in allowed:
        raise forms.ValidationError("فقط تصویر jpg یا png یا webp، و برای مجوز PDF هم مجاز است.")
    return upload


class SpecialtyMixin:
    def clean_specialties(self):
        value = self.cleaned_data.get("specialties") or []
        if len(value) > 5:
            raise forms.ValidationError("حداکثر ۵ تخصص مجاز است.")
        return value

    def clean_education(self):
        value = self.cleaned_data.get("education") or []
        if len(value) > 5:
            raise forms.ValidationError("حداکثر ۵ مورد تحصیلی مجاز است.")
        return value


class TherapistRegistrationForm(SpecialtyMixin, ClientRegistrationForm):
    display_name = forms.CharField(label="نام نمایشی", max_length=150)
    photo = forms.FileField(label="عکس", required=False)
    gender = forms.ChoiceField(label="جنسیت", choices=GENDERS)
    languages = forms.MultipleChoiceField(
        label="زبان‌ها",
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
    )
    years_experience = forms.IntegerField(label="سال تجربه", min_value=0, max_value=60)
    license_type = forms.ChoiceField(label="نوع مجوز", choices=LICENSE_TYPES)
    license_number = forms.CharField(label="شماره مجوز", max_length=80)
    license_country = forms.CharField(label="کشور صدور", max_length=80)
    phone = forms.CharField(label="شماره تماس", max_length=20, required=False)
    license_file = forms.FileField(label="فایل مجوز")
    specialties = forms.MultipleChoiceField(
        label="تخصص‌ها",
        choices=SPECIALTY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
        help_text="حداکثر ۵ مورد.",
    )
    education = forms.MultipleChoiceField(
        label="تحصیلات",
        choices=EDUCATION_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
        help_text="حداقل یک مورد.",
    )
    approach = forms.ChoiceField(label="رویکرد", choices=APPROACHES)
    introduction = forms.CharField(label="معرفی", max_length=4000, widget=forms.Textarea(attrs={"rows": 4}))
    currency = forms.ChoiceField(label="ارز", choices=CURRENCIES, initial="IRR")
    session_price = forms.DecimalField(
        label="قیمت جلسه",
        min_value=1,
        max_digits=12,
        decimal_places=2,
        help_text="برای تومان، مبلغ را به تومان بنویسید.",
    )
    timezone = forms.ChoiceField(label="منطقه زمانی", choices=TIMEZONES, initial="Asia/Tehran")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_groups = [
            ("حساب کاربری", ["first_name", "username", "email", "password1", "password2"]),
            ("پروفایل", ["display_name", "photo", "gender", "languages", "years_experience", "phone"]),
            ("مجوز", ["license_type", "license_number", "license_country", "license_file"]),
            ("کار درمانی", ["specialties", "education", "approach", "introduction", "currency", "session_price", "timezone"]),
        ]

    def clean_photo(self):
        return clean_upload(self.cleaned_data.get("photo"), PHOTO_EXTENSIONS)

    def clean_license_file(self):
        return clean_upload(self.cleaned_data.get("license_file"), UPLOAD_EXTENSIONS)

    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        with transaction.atomic():
            user = super().save(commit=True)
            group, _created = Group.objects.get_or_create(name=THERAPIST_GROUP_NAME)
            user.groups.add(group)
            profile = TherapistProfile(
                user=user,
                display_name=self.cleaned_data["display_name"],
                gender=self.cleaned_data["gender"],
                languages=self.cleaned_data["languages"],
                years_experience=self.cleaned_data["years_experience"],
                license_type=self.cleaned_data["license_type"],
                license_number=self.cleaned_data["license_number"],
                license_country=self.cleaned_data["license_country"],
                phone=self.cleaned_data.get("phone", ""),
                license_file=self.cleaned_data["license_file"],
                specialties=self.cleaned_data["specialties"],
                education=self.cleaned_data["education"],
                approach=self.cleaned_data["approach"],
                introduction=self.cleaned_data["introduction"],
                currency=self.cleaned_data["currency"],
                session_price=self.cleaned_data["session_price"],
                timezone=self.cleaned_data["timezone"],
                status=TherapistProfile.Status.PENDING,
            )
            if self.cleaned_data.get("photo"):
                profile.photo = self.cleaned_data["photo"]
            saved = False
            for _attempt in range(5):
                profile.slug = unique_slug(self.cleaned_data["display_name"])
                try:
                    with transaction.atomic():
                        profile.save()
                    saved = True
                    break
                except IntegrityError:
                    continue
            if not saved:
                raise IntegrityError("slug")
        return user


def chosen_week_cells(values):
    allowed = {item.strftime("%H:%M"): item for item in grid_starts()}
    chosen = set()
    for value in values:
        day_text, _, time_text = str(value).partition("-")
        start = allowed.get(time_text)
        if start and day_text.isdigit() and int(day_text) in range(7):
            chosen.add((int(day_text), start))
    return chosen


class AdminTherapistWizardForm(TherapistRegistrationForm):
    """Create an approved therapist and the weekly hours that make the profile public."""

    def clean(self):
        cleaned = super().clean()
        chosen = chosen_week_cells(self.data.getlist("cells"))
        if not chosen:
            self.add_error(None, "برای نمایش در سایت، حداقل یک ساعت هفتگی لازم است.")
        cleaned["cells"] = chosen
        return cleaned

    def save(self, commit=True):
        from therapy.services import replace_cells

        user = super().save(commit=commit)
        if not commit:
            return user
        profile = user.therapist_profile
        profile.status = TherapistProfile.Status.APPROVED
        profile.save()
        replace_cells(profile, self.cleaned_data["cells"])
        self.profile = profile
        return user


class TherapistProfileAdminForm(forms.ModelForm):
    """Chip choices for languages and education on the therapist edit page."""

    languages = forms.MultipleChoiceField(
        label="زبان‌ها",
        choices=LANGUAGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
    )
    education = forms.MultipleChoiceField(
        label="تحصیلات",
        choices=EDUCATION_CHOICES,
        required=False,
        help_text="حداکثر ۵ مورد.",
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
    )

    class Meta:
        model = TherapistProfile
        exclude = ("google_refresh_token",)

    def clean_education(self):
        value = self.cleaned_data.get("education") or []
        if len(value) > 5:
            raise forms.ValidationError("حداکثر ۵ مورد تحصیلی مجاز است.")
        return value


class TherapistProfileForm(SpecialtyMixin, forms.ModelForm):
    languages = forms.MultipleChoiceField(
        label="زبان‌ها",
        choices=LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
    )
    specialties = forms.MultipleChoiceField(
        label="تخصص‌ها",
        choices=SPECIALTY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
        help_text="حداکثر ۵ مورد.",
    )
    education = forms.MultipleChoiceField(
        label="تحصیلات",
        choices=EDUCATION_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "choice-grid"}),
        help_text="حداقل یک مورد.",
    )

    class Meta:
        model = TherapistProfile
        fields = [
            "display_name",
            "photo",
            "gender",
            "languages",
            "years_experience",
            "license_type",
            "license_number",
            "license_country",
            "phone",
            "license_file",
            "specialties",
            "education",
            "approach",
            "introduction",
            "currency",
            "session_price",
            "timezone",
        ]
        widgets = {"introduction": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["photo"].required = False
        self.fields["license_file"].required = False
        self.fields["session_price"].help_text = "برای تومان، مبلغ را به تومان بنویسید."

    def clean_photo(self):
        return clean_upload(self.cleaned_data.get("photo"), PHOTO_EXTENSIONS)

    def clean_license_file(self):
        return clean_upload(self.cleaned_data.get("license_file"), UPLOAD_EXTENSIONS)


class ReceiptForm(forms.Form):
    amount = forms.DecimalField(label="مبلغ پرداخت‌شده", min_value=0, max_digits=12, decimal_places=2)
    reference = forms.CharField(label="شماره پیگیری", max_length=120)
    note = forms.CharField(
        label="توضیح برای درمانگر",
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    attachment = forms.FileField(label="تصویر رسید", required=False)

    def clean_attachment(self):
        return clean_upload(self.cleaned_data.get("attachment"), UPLOAD_EXTENSIONS)


class ClosureForm(forms.Form):
    on = forms.CharField(label="تاریخ شمسی", help_text="مثل 1404-08-21")
    all_day = forms.BooleanField(label="بستن همهٔ روز", required=False)
    start = forms.ChoiceField(label="ساعت", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        times = [(item.strftime("%H:%M"), item.strftime("%H:%M")) for item in grid_starts()]
        self.fields["start"].choices = [("", "یک ساعت")] + times

    def clean(self):
        cleaned = super().clean()
        try:
            cleaned["day"] = parse_jalali_date(cleaned.get("on") or "")
        except ValueError:
            raise forms.ValidationError("تاریخ شمسی معتبر نیست.") from None
        if cleaned.get("all_day"):
            cleaned["start_time"] = None
        elif cleaned.get("start"):
            hour, minute = cleaned["start"].split(":")
            from datetime import time

            cleaned["start_time"] = time(int(hour), int(minute))
        else:
            raise forms.ValidationError("ساعت را انتخاب کنید یا همهٔ روز را ببندید.")
        return cleaned


class AddStudentForm(forms.Form):
    first_name = forms.CharField(label="نام", max_length=150)
    username = forms.CharField(label="نام کاربری", max_length=150)
    email = forms.EmailField(label="ایمیل")
    password = forms.CharField(
        label="گذرواژهٔ اولیه",
        widget=forms.PasswordInput,
        help_text="حساب تازه‌ای ساخته می‌شود. این گذرواژه را فقط به همان مراجع بدهید.",
    )

    def __init__(self, profile, *args, **kwargs):
        self.profile = profile
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        username = (cleaned.get("username") or "").strip()
        email = (cleaned.get("email") or "").strip().lower()
        cleaned["username"] = username
        cleaned["email"] = email
        if not username or not email:
            return cleaned
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("این نام کاربری قبلاً ثبت شده است.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("این ایمیل قبلاً ثبت شده است.")
        try:
            validate_password(cleaned.get("password") or "")
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages[0]) from exc
        return cleaned


class TaskForm(forms.Form):
    client = forms.ModelChoiceField(label="مراجع", queryset=User.objects.none())
    kind = forms.ChoiceField(
        label="نوع",
        choices=(("practice", "تمرین"), ("reminder", "یادآور")),
    )
    title = forms.CharField(label="عنوان", max_length=120)
    body = forms.CharField(label="شرح", widget=forms.Textarea(attrs={"rows": 3}))
    reward = forms.CharField(label="پاداش", max_length=200, required=False)
    due_on = forms.DateField(label="تاریخ", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, profile, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = User.objects.filter(care_links__therapist=profile).order_by("first_name", "username")
        self.fields["client"].label_from_instance = lambda user: user.get_full_name() or user.get_username()


_RECORD_FIELDS = ["notes", "mind_map", "reports", "pre_session_summary"]


class RecordForm(forms.ModelForm):
    class Meta:
        model = ClientRecord
        fields = _RECORD_FIELDS
        widgets = {name: forms.Textarea(attrs={"rows": 4}) for name in _RECORD_FIELDS}


class SessionUpdateForm(forms.Form):
    meet_url = forms.URLField(label="پیوند ورود", required=False)
    summary = forms.CharField(label="خلاصه برای مراجع", required=False, widget=forms.Textarea(attrs={"rows": 3}))


class MoodForm(forms.Form):
    emoji = forms.ChoiceField(label="حال", choices=())
    word = forms.CharField(label="یک کلمه", max_length=40)

    def __init__(self, *args, **kwargs):
        from therapy.choices import MOODS

        super().__init__(*args, **kwargs)
        self.fields["emoji"].choices = MOODS


class TelegramForm(forms.Form):
    telegram_username = forms.CharField(label="نام کاربری تلگرام", max_length=32, required=False)

    def clean_telegram_username(self):
        value = (self.cleaned_data.get("telegram_username") or "").strip().lstrip("@")
        if value and not re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
            raise forms.ValidationError("نام کاربری تلگرام معتبر نیست.")
        return value
