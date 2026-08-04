from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import Assignment, AssignmentRequest, Company, ContactAttempt, InviteCode, Notice, Resource, VisitNote, Message, Reply

_fc = {'class': 'form-control'}
_fs = {'class': 'form-select'}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Email or username',
        widget=forms.TextInput(attrs={**_fc, 'autofocus': True}),
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        if username and '@' in username:
            matches = User.objects.filter(email__iexact=username.strip())
            if matches.count() == 1:
                self.cleaned_data['username'] = matches.first().get_username()
        return super().clean()


class RegisterForm(forms.Form):
    first_name  = forms.CharField(max_length=50, required=False,
                                  widget=forms.TextInput(attrs={**_fc, 'placeholder': 'First name'}))
    last_name   = forms.CharField(max_length=50, required=False,
                                  widget=forms.TextInput(attrs={**_fc, 'placeholder': 'Last name'}))
    email       = forms.EmailField(
                                  widget=forms.EmailInput(attrs={**_fc, 'placeholder': 'Email address'}))
    password1   = forms.CharField(label='Password',
                                  widget=forms.PasswordInput(attrs=_fc))
    password2   = forms.CharField(label='Confirm Password',
                                  widget=forms.PasswordInput(attrs=_fc))
    invite_code = forms.CharField(
        max_length=40,
        help_text="Enter the invite code provided by your admin.",
        widget=forms.TextInput(attrs={**_fc, 'placeholder': 'Invite code'}),
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email

    def clean_invite_code(self):
        code = self.cleaned_data['invite_code'].strip()
        try:
            invite = InviteCode.objects.get(code=code)
        except InviteCode.DoesNotExist:
            raise forms.ValidationError("Invalid invite code.")
        if not invite.is_available:
            raise forms.ValidationError("This invite code has already been used.")
        self._invite = invite
        return code

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', "Passwords do not match.")
        return cleaned

    def save(self):
        from django.utils import timezone
        email      = self.cleaned_data['email']
        first_name = self.cleaned_data.get('first_name', '')
        last_name  = self.cleaned_data.get('last_name', '')

        base = email.split('@')[0].lower()
        base = ''.join(c for c in base if c.isalnum() or c in '._-')[:30]
        username = base
        suffix = 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{suffix}"
            suffix += 1

        user = User.objects.create_user(
            username=username,
            email=email,
            password=self.cleaned_data['password1'],
            first_name=first_name,
            last_name=last_name,
        )
        self._invite.used_by = user
        self._invite.used_at = timezone.now()
        self._invite.save(update_fields=['used_by', 'used_at'])
        return user


# ---------------------------------------------------------------------------
# Company Visitation
# ---------------------------------------------------------------------------

class ContactAttemptForm(forms.ModelForm):
    class Meta:
        model  = ContactAttempt
        fields = ('method', 'notes')
        widgets = {
            'method': forms.Select(attrs={'class': 'form-select'}),
            'notes':  forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'What happened? (optional)',
            }),
        }


class CompanyContactUpdateForm(forms.ModelForm):
    class Meta:
        model  = Company
        fields = ('primary_contact_name', 'primary_contact_title', 'phone', 'email')
        widgets = {
            'primary_contact_name':  forms.TextInput(attrs={**_fc, 'placeholder': 'Contact name'}),
            'primary_contact_title': forms.TextInput(attrs={**_fc, 'placeholder': 'Title'}),
            'phone': forms.TextInput(attrs={**_fc, 'placeholder': 'Phone'}),
            'email': forms.EmailInput(attrs={**_fc, 'placeholder': 'Email'}),
        }
        labels = {
            'primary_contact_name':  'Name',
            'primary_contact_title': 'Title',
            'phone': 'Phone',
            'email': 'Email',
        }


class VisitNoteForm(forms.ModelForm):
    class Meta:
        model  = VisitNote
        fields = (
            'contact_name',
            'additional_contact_name', 'additional_contact_title',
            'additional_contact_phone', 'additional_contact_email',
            'notes',
            'hiring_status',
            'employee_count', 'jobs_added_expected',
            'jobs_added_last_year', 'jobs_lost_last_year',
            'building_size_sqft', 'at_capacity',
            'expansion_adding_sq_footage', 'expansion_new_building',
            'expansion_adding_equipment', 'expansion_capex_planned',
            'expansion_notes',
            'volunteer_helped', 'volunteer_helped_notes',
            'received_business_lead',
            'follow_up_needed', 'follow_up_notes',
        )
        widgets = {
            'contact_name': forms.TextInput(attrs={**_fc, 'placeholder': 'Name of person you spoke with'}),
            'additional_contact_name':  forms.TextInput(attrs={**_fc, 'placeholder': 'Name'}),
            'additional_contact_title': forms.TextInput(attrs={**_fc, 'placeholder': 'Title'}),
            'additional_contact_phone': forms.TextInput(attrs={**_fc, 'placeholder': 'Phone'}),
            'additional_contact_email': forms.EmailInput(attrs={**_fc, 'placeholder': 'Email'}),
            'notes': forms.Textarea(attrs={**_fc, 'rows': 5,
                'placeholder': 'What did you learn? What was the general tone of the conversation?'}),
            'hiring_status':        forms.Select(attrs=_fs),
            'employee_count':       forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 45',    'min': 0}),
            'jobs_added_expected':  forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 10',    'min': 0}),
            'jobs_added_last_year': forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 5',     'min': 0}),
            'jobs_lost_last_year':  forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 2',     'min': 0}),
            'building_size_sqft':   forms.NumberInput(attrs={**_fc, 'placeholder': 'e.g. 12000', 'min': 0}),
            'at_capacity':          forms.Select(attrs=_fs),
            'expansion_adding_sq_footage': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_new_building':      forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_adding_equipment':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_capex_planned':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expansion_notes':        forms.Textarea(attrs={**_fc, 'rows': 2,
                'placeholder': 'Additional expansion details (optional)'}),
            'volunteer_helped':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'volunteer_helped_notes': forms.Textarea(attrs={**_fc, 'rows': 3,
                'placeholder': 'Describe how you assisted...'}),
            'received_business_lead': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_needed':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_notes':        forms.Textarea(attrs={**_fc, 'rows': 3,
                'placeholder': 'Describe the follow-up needed (optional)'}),
        }
        labels = {
            'contact_name':            'Who did you speak with?',
            'additional_contact_name': 'Name',
            'notes':                   'Visit Notes',
            'hiring_status':           'Hiring / Layoff Status',
            'employee_count':          'Current Employees',
            'jobs_added_expected':     'Expected Jobs to be Added',
            'jobs_added_last_year':    'Jobs Added Last Year',
            'jobs_lost_last_year':     'Jobs Lost Last Year',
            'building_size_sqft':      'Current Building Size (sq ft)',
            'at_capacity':             'At Capacity?',
            'expansion_adding_sq_footage': 'Adding square footage',
            'expansion_new_building':      'Looking for / moving to a new building',
            'expansion_adding_equipment':  'Adding equipment',
            'expansion_capex_planned':     'Capital expenditure planned',
            'expansion_notes':             'Expansion details',
            'volunteer_helped':            'I assisted this company with a problem during this visit',
            'volunteer_helped_notes':      'How did you assist?',
            'received_business_lead':      'I received a business lead or referral from this visit',
            'follow_up_needed':            'Follow-up needed?',
            'follow_up_notes':             'Follow-up Details',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Required on form but blank=True on model to allow existing rows without a value
        self.fields['hiring_status'].required = True


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class MessageForm(forms.ModelForm):
    class Meta:
        model  = Message
        fields = ('subject', 'body', 'is_private')
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject',
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Write your message...',
            }),
            'is_private': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_private': 'Send as private message to admin',
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model  = Reply
        fields = ('body',)
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Write a reply...',
            }),
        }
        labels = {'body': ''}


# ---------------------------------------------------------------------------
# Admin (portal-side)
# ---------------------------------------------------------------------------

class InviteAdminForm(forms.Form):
    first_name   = forms.CharField(max_length=50, required=False,
                                   widget=forms.TextInput(attrs={**_fc, 'placeholder': 'First name'}))
    last_name    = forms.CharField(max_length=50, required=False,
                                   widget=forms.TextInput(attrs={**_fc, 'placeholder': 'Last name'}))
    email        = forms.EmailField(widget=forms.EmailInput(attrs={**_fc, 'placeholder': 'Email address'}))
    is_superuser = forms.BooleanField(required=False, label='Grant superuser privileges',
                                      help_text='Superusers have full access including the Django admin panel.',
                                      widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email already exists.")
        return email


class QuickCompanyForm(forms.ModelForm):
    class Meta:
        model  = Company
        fields = ('name', 'industry', 'address', 'city', 'state', 'zip_code', 'phone', 'email',
                  'primary_contact_name', 'is_browse_visible')
        widgets = {
            'name':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company name'}),
            'industry':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Industry'}),
            'address':              forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'city':                 forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state':                forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'zip_code':             forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Zip code'}),
            'phone':                forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}),
            'email':                forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'primary_contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact name'}),
            'is_browse_visible':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CompanyManagementForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = (
            'name', 'status', 'industry', 'address', 'city', 'state', 'zip_code',
            'phone', 'email', 'website', 'primary_contact_name',
            'primary_contact_title', 'notes', 'imported_last_visit_date',
            'is_browse_visible',
        )
        widgets = {
            'name':                  forms.TextInput(attrs=_fc),
            'status':                forms.Select(attrs={'class': 'form-select'}),
            'industry':              forms.TextInput(attrs=_fc),
            'address':               forms.TextInput(attrs=_fc),
            'city':                  forms.TextInput(attrs=_fc),
            'state':                 forms.TextInput(attrs=_fc),
            'zip_code':              forms.TextInput(attrs=_fc),
            'phone':                 forms.TextInput(attrs=_fc),
            'email':                 forms.EmailInput(attrs=_fc),
            'website':               forms.URLInput(attrs=_fc),
            'primary_contact_name':  forms.TextInput(attrs=_fc),
            'primary_contact_title': forms.TextInput(attrs=_fc),
            'notes':                 forms.Textarea(attrs={**_fc, 'rows': 5}),
            'imported_last_visit_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'is_browse_visible':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_status(self):
        status = self.cleaned_data['status']
        if not self.instance.pk:
            return status

        has_active_assignment = self.instance.assignments.filter(
            status=Assignment.STATUS_ACTIVE,
        ).exists()
        if has_active_assignment and status != Company.STATUS_ASSIGNED:
            raise forms.ValidationError(
                'This company has an active assignment, so its status must remain Assigned.'
            )
        if not has_active_assignment and status == Company.STATUS_ASSIGNED:
            raise forms.ValidationError(
                'Assign the company to a volunteer or admin before setting its status to Assigned.'
            )
        return status


class _CompanyWithIndustryField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} — {obj.industry}" if obj.industry else obj.name


class _AssigneeChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        name = obj.get_full_name() or obj.username
        role = 'Admin' if obj.is_staff else 'Volunteer'
        return f'{name} ({role})'


class QuickAssignForm(forms.Form):
    company = _CompanyWithIndustryField(
        queryset=Company.objects.filter(
            status=Company.STATUS_UNASSIGNED,
            is_archived=False,
        ).order_by('industry', 'name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='Select a company...',
    )
    volunteer = _AssigneeChoiceField(
        queryset=User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
        label='Assignee',
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='Select a volunteer or admin...',
    )


# ---------------------------------------------------------------------------
# Admin (Django admin)
# ---------------------------------------------------------------------------

class CompanyCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='CSV File',
        help_text=(
            'Required column: <strong>name</strong>. '
            'Optional: address, city, state, zip_code, phone, email, website, '
            'industry, primary_contact_name, primary_contact_title, notes, '
            'last_visit_date'
        ),
        widget=forms.FileInput(attrs={'accept': '.csv', 'class': 'form-control'}),
    )
    overwrite_existing = forms.BooleanField(
        required=False,
        initial=False,
        label='Update existing companies by name',
        help_text=(
            'Archived companies with matching names are restored automatically. '
            'If checked, matching company details are also updated from the CSV.'
        ),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )


class NoticeForm(forms.ModelForm):
    class Meta:
        model  = Notice
        fields = ('title', 'body', 'link_url', 'link_text', 'is_active', 'expires_at')
        widgets = {
            'title':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Volunteer Appreciation Night — June 15'}),
            'body':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional details...'}),
            'link_url':   forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'link_text':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. RSVP here'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        labels = {
            'link_url':   'Button link (optional)',
            'link_text':  'Button label (optional)',
            'expires_at': 'Expires at',
        }


class VisitExportForm(forms.Form):
    date_from = forms.DateField(
        required=False,
        label='From',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
    date_to = forms.DateField(
        required=False,
        label='To',
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
    )
    industry = forms.ChoiceField(
        required=False,
        label='Industry',
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    volunteer = forms.ModelChoiceField(
        required=False,
        label='Volunteer',
        queryset=User.objects.filter(is_active=True, is_staff=False).order_by('first_name', 'last_name'),
        empty_label='All volunteers',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        industries = (
            Company.objects.exclude(industry='')
            .values_list('industry', flat=True)
            .distinct().order_by('industry')
        )
        self.fields['industry'].choices = [('', 'All industries')] + [(i, i) for i in industries]


class AccountForm(forms.ModelForm):
    phone_number = forms.CharField(
        max_length=20, required=False,
        label='Mobile Phone (for SMS reminders)',
        widget=forms.TextInput(attrs={**_fc, 'placeholder': 'e.g. +17755551234'}),
    )
    sms_reminders_enabled = forms.BooleanField(
        required=False,
        label='Send me text message reminders when I have inactive assignments',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs=_fc),
            'last_name':  forms.TextInput(attrs=_fc),
            'email':      forms.EmailInput(attrs=_fc),
        }

    def __init__(self, *args, **kwargs):
        profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if profile:
            self.fields['phone_number'].initial = profile.phone_number
            self.fields['sms_reminders_enabled'].initial = profile.sms_reminders_enabled

    def clean_email(self):
        email = self.cleaned_data['email']
        qs = User.objects.exclude(pk=self.instance.pk).filter(email=email)
        if qs.exists():
            raise forms.ValidationError("That email address is already in use.")
        return email

    def clean(self):
        cleaned = super().clean()
        sms_on = cleaned.get('sms_reminders_enabled')
        phone  = cleaned.get('phone_number', '').strip()
        if sms_on and not phone:
            self.add_error('phone_number', 'Enter a mobile number to enable SMS reminders.')
        return cleaned


class ResourceForm(forms.ModelForm):
    class Meta:
        model  = Resource
        fields = ['title', 'description', 'category', 'url', 'sort_order', 'is_active']
        widgets = {
            'title':       forms.TextInput(attrs=_fc),
            'description': forms.Textarea(attrs={**_fc, 'rows': 3}),
            'category':    forms.Select(attrs=_fs),
            'url':         forms.URLInput(attrs={**_fc, 'placeholder': 'https://'}),
            'sort_order':  forms.NumberInput(attrs=_fc),
        }
