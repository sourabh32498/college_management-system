from django import forms
from django.utils import timezone

from .models import (
    Student,
    AdmissionApplication,
    AttendanceRecord,
    ExamSchedule,
    ExamResult,
    FeeStructure,
    FeeInvoice,
    FeePayment,
    Room,
    TimetableEntry,
)

from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User


def _set_field_class(form, field_name, base_class):
    classes = [base_class]
    if form.is_bound and form.errors.get(field_name):
        classes.append('is-invalid')
    form.fields[field_name].widget.attrs['class'] = ' '.join(classes)


class CustomAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_field_class(self, 'username', 'form-control')
        _set_field_class(self, 'password', 'form-control')
        self.fields['username'].widget.attrs.update({'placeholder': 'Username', 'autofocus': True})
        self.fields['password'].widget.attrs.update({'placeholder': 'Password'})


class CustomUserCreationForm(UserCreationForm):
    """User registration form with Bootstrap styling."""
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    first_name = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_field_class(self, 'username', 'form-control')
        _set_field_class(self, 'email', 'form-control')
        _set_field_class(self, 'first_name', 'form-control')
        _set_field_class(self, 'last_name', 'form-control')
        _set_field_class(self, 'password1', 'form-control')
        _set_field_class(self, 'password2', 'form-control')
        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm Password'

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already registered.')
        return email


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_field_class(self, 'email', 'form-control')
        self.fields['email'].widget.attrs.update({
            'placeholder': 'name@example.com',
        })


class CustomSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_field_class(self, 'new_password1', 'form-control')
        _set_field_class(self, 'new_password2', 'form-control')
        self.fields['new_password1'].widget.attrs.update({
            'placeholder': 'New password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'placeholder': 'Confirm new password',
        })


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['seat_number', 'mother_name', 'father_name', 'parent_name', 'first_name', 'last_name', 'email', 'enrollment_date', 'course', 'gpa', 'is_active']
        widgets = {
            'enrollment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_gpa(self):
        gpa = self.cleaned_data.get('gpa')
        if gpa is None:
            return gpa
        # Ensure reasonable GPA range (0.0 - 4.0)
        if gpa < 0 or gpa > 4:
            raise forms.ValidationError('GPA must be between 0.0 and 4.0')
        return gpa

    def clean_enrollment_date(self):
        enrollment_date = self.cleaned_data.get('enrollment_date')
        if enrollment_date and enrollment_date > timezone.localdate():
            raise forms.ValidationError('Enrollment date cannot be in the future.')
        return enrollment_date

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.strip().lower()
        return email

    def clean_seat_number(self):
        seat_number = self.cleaned_data.get('seat_number')
        if seat_number:
            return seat_number.strip().upper()
        return seat_number

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.CheckboxInput):
                classes = ['form-check-input']
                if self.is_bound and self.errors.get(field_name):
                    classes.append('is-invalid')
                field.widget.attrs['class'] = ' '.join(classes)
            else:
                classes = [f"{existing} form-control".strip()]
                if self.is_bound and self.errors.get(field_name):
                    classes.append('is-invalid')
                field.widget.attrs['class'] = ' '.join(classes).strip()
                if field_name == 'gpa':
                    field.widget.attrs['placeholder'] = 'e.g. 3.75'
                if field_name == 'seat_number':
                    field.widget.attrs['placeholder'] = 'e.g. S01423'
                if field_name == 'parent_name':
                    field.widget.attrs['placeholder'] = 'Mother or Father Name'
                if field_name == 'mother_name':
                    field.widget.attrs['placeholder'] = "Student's mother name"
                if field_name == 'father_name':
                    field.widget.attrs['placeholder'] = "Student's father name"


class OnlineResultSearchForm(forms.Form):
    seat_number = forms.CharField(max_length=30, label='Seat Number')
    mother_name = forms.CharField(max_length=120, label="Mother's Name")
    father_name = forms.CharField(max_length=120, label="Father's Name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _set_field_class(self, 'seat_number', 'form-control')
        _set_field_class(self, 'mother_name', 'form-control')
        _set_field_class(self, 'father_name', 'form-control')
        self.fields['seat_number'].widget.attrs.update({'placeholder': 'Enter seat number'})
        self.fields['mother_name'].widget.attrs.update({'placeholder': "Enter mother's name"})
        self.fields['father_name'].widget.attrs.update({'placeholder': "Enter father's name"})

    def clean_seat_number(self):
        return self.cleaned_data['seat_number'].strip().upper()

    def clean_mother_name(self):
        return self.cleaned_data['mother_name'].strip()

    def clean_father_name(self):
        return self.cleaned_data['father_name'].strip()


class BootstrapModelForm(forms.ModelForm):
    """Base model form that applies Bootstrap classes consistently."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            existing = field.widget.attrs.get('class', '')
            if isinstance(field.widget, forms.CheckboxInput):
                classes = ['form-check-input']
                if self.is_bound and self.errors.get(field_name):
                    classes.append('is-invalid')
                field.widget.attrs['class'] = ' '.join(classes)
            else:
                classes = [f"{existing} form-control".strip()]
                if self.is_bound and self.errors.get(field_name):
                    classes.append('is-invalid')
                field.widget.attrs['class'] = ' '.join(classes).strip()


class AdmissionApplicationForm(BootstrapModelForm):
    class Meta:
        model = AdmissionApplication
        fields = ['student', 'program', 'session', 'application_date', 'merit_score', 'status', 'notes']
        widgets = {
            'application_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class AttendanceRecordForm(BootstrapModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ['student', 'attendance_date', 'status', 'remarks']
        widgets = {
            'attendance_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ExamScheduleForm(BootstrapModelForm):
    class Meta:
        model = ExamSchedule
        fields = ['title', 'course', 'subject', 'exam_type', 'exam_date', 'start_time', 'end_time', 'room', 'max_marks']
        widgets = {
            'exam_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        if start and end and end <= start:
            self.add_error('end_time', 'End time must be after start time.')
        return cleaned


class ExamResultForm(BootstrapModelForm):
    class Meta:
        model = ExamResult
        fields = ['student', 'exam', 'marks_obtained', 'grade']

    def clean(self):
        cleaned = super().clean()
        exam = cleaned.get('exam')
        marks = cleaned.get('marks_obtained')
        if exam and marks is not None and marks > exam.max_marks:
            self.add_error('marks_obtained', f'Marks cannot exceed max marks ({exam.max_marks}).')
        return cleaned


class FeeStructureForm(BootstrapModelForm):
    class Meta:
        model = FeeStructure
        fields = ['name', 'course', 'academic_year', 'total_amount', 'due_days', 'is_active']


class FeeInvoiceForm(BootstrapModelForm):
    class Meta:
        model = FeeInvoice
        fields = [
            'student', 'fee_structure', 'invoice_number', 'issue_date', 'due_date',
            'total_amount', 'discount_amount', 'scholarship_amount', 'status',
        ]
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        issue_date = cleaned.get('issue_date')
        due_date = cleaned.get('due_date')
        total_amount = cleaned.get('total_amount') or 0
        discount = cleaned.get('discount_amount') or 0
        scholarship = cleaned.get('scholarship_amount') or 0
        if issue_date and due_date and due_date < issue_date:
            self.add_error('due_date', 'Due date cannot be before issue date.')
        if (discount + scholarship) > total_amount:
            self.add_error('discount_amount', 'Discount and scholarship together cannot exceed total amount.')
        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active_structures = FeeStructure.objects.filter(is_active=True).order_by('course', 'name')
        if active_structures.exists():
            self.fields['fee_structure'].queryset = active_structures
        else:
            self.fields['fee_structure'].queryset = FeeStructure.objects.order_by('course', 'name')
        self.fields['fee_structure'].empty_label = 'Select fee structure'
        self.fields['fee_structure'].label_from_instance = (
            lambda obj: f"{obj.name} | {obj.course} | {obj.academic_year} | {obj.total_amount}"
        )


class FeePaymentForm(BootstrapModelForm):
    class Meta:
        model = FeePayment
        fields = ['invoice', 'payment_date', 'amount', 'method', 'transaction_reference', 'notes']
        widgets = {
            'payment_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned = super().clean()
        invoice = cleaned.get('invoice')
        amount = cleaned.get('amount')
        if amount is not None and amount <= 0:
            self.add_error('amount', 'Payment amount must be greater than zero.')
        if invoice and amount:
            if amount > invoice.due_amount:
                self.add_error('amount', f'Amount cannot exceed due amount ({invoice.due_amount}).')
        return cleaned


class RoomForm(BootstrapModelForm):
    class Meta:
        model = Room
        fields = ['name', 'capacity', 'is_lab']


class TimetableEntryForm(BootstrapModelForm):
    class Meta:
        model = TimetableEntry
        fields = ['course', 'section', 'subject', 'faculty_name', 'weekday', 'start_time', 'end_time', 'room']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_time')
        end = cleaned.get('end_time')
        room = cleaned.get('room')
        weekday = cleaned.get('weekday')
        if start and end and end <= start:
            self.add_error('end_time', 'End time must be after start time.')
            return cleaned

        if all([room, weekday, start, end]):
            qs = TimetableEntry.objects.filter(room=room, weekday=weekday)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            has_conflict = qs.filter(start_time__lt=end, end_time__gt=start).exists()
            if has_conflict:
                self.add_error('room', 'Room conflict detected for this time slot.')
        return cleaned
