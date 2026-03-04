from django.db import models, transaction
import re


class Student(models.Model):
	seat_number = models.CharField(max_length=30, unique=True, null=True, blank=True)
	date_of_birth = models.DateField(null=True, blank=True)
	mother_name = models.CharField(max_length=120, blank=True)
	father_name = models.CharField(max_length=120, blank=True)
	parent_name = models.CharField(max_length=120, blank=True)
	first_name = models.CharField(max_length=50)
	last_name = models.CharField(max_length=50)
	email = models.EmailField(unique=True)
	enrollment_date = models.DateField()
	course = models.CharField(max_length=100)
	gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-enrollment_date', 'last_name', 'first_name']

	def __str__(self):
		return f"{self.first_name} {self.last_name}"

	@classmethod
	def _generate_seat_number(cls):
		max_number = 0
		for value in cls.objects.exclude(seat_number__isnull=True).exclude(seat_number='').values_list('seat_number', flat=True):
			match = re.match(r'^S(\d+)$', (value or '').strip().upper())
			if not match:
				continue
			max_number = max(max_number, int(match.group(1)))
		return f"S{max_number + 1:05d}"

	def save(self, *args, **kwargs):
		if self.seat_number:
			self.seat_number = self.seat_number.strip().upper()
		with transaction.atomic():
			if not self.seat_number:
				candidate = self._generate_seat_number()
				while Student.objects.filter(seat_number=candidate).exists():
					candidate = self._generate_seat_number()
				self.seat_number = candidate
			super().save(*args, **kwargs)


class AdmissionApplication(models.Model):
	class Status(models.TextChoices):
		DRAFT = 'draft', 'Draft'
		SUBMITTED = 'submitted', 'Submitted'
		UNDER_REVIEW = 'under_review', 'Under Review'
		SHORTLISTED = 'shortlisted', 'Shortlisted'
		ACCEPTED = 'accepted', 'Accepted'
		REJECTED = 'rejected', 'Rejected'

	student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='admission_applications')
	program = models.CharField(max_length=120)
	session = models.CharField(max_length=50, help_text='e.g. 2026-27')
	application_date = models.DateField()
	merit_score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-application_date', '-created_at']

	def __str__(self):
		return f"{self.student} - {self.program} ({self.status})"


class AttendanceRecord(models.Model):
	class Status(models.TextChoices):
		PRESENT = 'present', 'Present'
		ABSENT = 'absent', 'Absent'
		LATE = 'late', 'Late'
		EXCUSED = 'excused', 'Excused'

	student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
	attendance_date = models.DateField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PRESENT)
	remarks = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-attendance_date', 'student__last_name']
		unique_together = ('student', 'attendance_date')

	def __str__(self):
		return f"{self.student} - {self.attendance_date} ({self.status})"


class ExamSchedule(models.Model):
	class ExamType(models.TextChoices):
		QUIZ = 'quiz', 'Quiz'
		MIDTERM = 'midterm', 'Midterm'
		FINAL = 'final', 'Final'
		PRACTICAL = 'practical', 'Practical'

	title = models.CharField(max_length=120)
	course = models.CharField(max_length=100)
	subject = models.CharField(max_length=120)
	exam_type = models.CharField(max_length=20, choices=ExamType.choices, default=ExamType.MIDTERM)
	exam_date = models.DateField()
	start_time = models.TimeField()
	end_time = models.TimeField()
	room = models.CharField(max_length=50, blank=True)
	max_marks = models.PositiveIntegerField(default=100)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-exam_date', 'start_time']

	def __str__(self):
		return f"{self.title} - {self.subject} ({self.exam_date})"


class Subject(models.Model):
	code = models.CharField(max_length=30)
	name = models.CharField(max_length=120)
	course = models.CharField(max_length=100)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['course', 'code']
		unique_together = ('course', 'code')

	def __str__(self):
		return f"{self.code} - {self.name} ({self.course})"


class ExamFormSubmission(models.Model):
	student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_form_submissions')
	semester = models.CharField(max_length=20, help_text='e.g. SEM-1')
	exam_session = models.CharField(max_length=20, help_text='e.g. 2026-27')
	address = models.CharField(max_length=255, blank=True)
	mobile_number = models.CharField(max_length=20, blank=True)
	gender = models.CharField(max_length=20, blank=True)
	category = models.CharField(max_length=20, blank=True)
	medium = models.CharField(max_length=30, default='English')
	selected_subject_codes = models.TextField(blank=True, help_text='Comma-separated subject codes selected in exam form')
	declaration_accepted = models.BooleanField(default=True)
	submitted_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-submitted_at']
		unique_together = ('student', 'semester', 'exam_session')

	def __str__(self):
		return f"{self.student} - {self.semester} ({self.exam_session})"


class ExamFormSubjectSelection(models.Model):
	submission = models.ForeignKey(ExamFormSubmission, on_delete=models.CASCADE, related_name='subject_selections')
	subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='exam_form_selections')
	is_selected = models.BooleanField(default=True)
	component_internal = models.BooleanField(default=False)
	component_theory = models.BooleanField(default=True)
	component_online = models.BooleanField(default=False)
	component_practical = models.BooleanField(default=False)
	component_oral = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['subject__code']
		unique_together = ('submission', 'subject')

	def __str__(self):
		return f"{self.submission_id} - {self.subject.code}"


class ExamResult(models.Model):
	student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_results')
	exam = models.ForeignKey(ExamSchedule, on_delete=models.CASCADE, related_name='results')
	marks_obtained = models.DecimalField(max_digits=6, decimal_places=2)
	grade = models.CharField(max_length=4, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-exam__exam_date', 'student__last_name']
		unique_together = ('student', 'exam')

	def __str__(self):
		return f"{self.student} - {self.exam}: {self.marks_obtained}"


class FeeStructure(models.Model):
	name = models.CharField(max_length=120)
	course = models.CharField(max_length=100)
	academic_year = models.CharField(max_length=20, help_text='e.g. 2026-27')
	total_amount = models.DecimalField(max_digits=10, decimal_places=2)
	due_days = models.PositiveIntegerField(default=30)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-academic_year', 'course', 'name']

	def __str__(self):
		return f"{self.name} - {self.course} ({self.academic_year})"


class FeeInvoice(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		PARTIAL = 'partial', 'Partially Paid'
		PAID = 'paid', 'Paid'
		OVERDUE = 'overdue', 'Overdue'

	student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_invoices')
	fee_structure = models.ForeignKey(FeeStructure, on_delete=models.PROTECT, related_name='invoices')
	invoice_number = models.CharField(max_length=40, unique=True)
	issue_date = models.DateField()
	due_date = models.DateField()
	total_amount = models.DecimalField(max_digits=10, decimal_places=2)
	discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	scholarship_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-issue_date', '-created_at']

	def __str__(self):
		return f"{self.invoice_number} - {self.student}"

	@property
	def payable_amount(self):
		base = self.total_amount - self.discount_amount - self.scholarship_amount
		return base if base > 0 else 0

	@property
	def paid_amount(self):
		total_paid = self.payments.aggregate(total=models.Sum('amount'))['total'] or 0
		return total_paid

	@property
	def due_amount(self):
		due = self.payable_amount - self.paid_amount
		return due if due > 0 else 0


class FeePayment(models.Model):
	class Method(models.TextChoices):
		CASH = 'cash', 'Cash'
		CARD = 'card', 'Card'
		UPI = 'upi', 'UPI'
		BANK = 'bank', 'Bank Transfer'

	invoice = models.ForeignKey(FeeInvoice, on_delete=models.CASCADE, related_name='payments')
	payment_date = models.DateField()
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	method = models.CharField(max_length=20, choices=Method.choices, default=Method.UPI)
	transaction_reference = models.CharField(max_length=100, blank=True)
	notes = models.CharField(max_length=255, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-payment_date', '-created_at']

	def __str__(self):
		return f"{self.invoice.invoice_number} - {self.amount}"


class Room(models.Model):
	name = models.CharField(max_length=40, unique=True)
	capacity = models.PositiveIntegerField(default=40)
	is_lab = models.BooleanField(default=False)

	class Meta:
		ordering = ['name']

	def __str__(self):
		return self.name


class TimetableEntry(models.Model):
	class Weekday(models.TextChoices):
		MONDAY = 'monday', 'Monday'
		TUESDAY = 'tuesday', 'Tuesday'
		WEDNESDAY = 'wednesday', 'Wednesday'
		THURSDAY = 'thursday', 'Thursday'
		FRIDAY = 'friday', 'Friday'
		SATURDAY = 'saturday', 'Saturday'

	course = models.CharField(max_length=100)
	section = models.CharField(max_length=20)
	subject = models.CharField(max_length=120)
	faculty_name = models.CharField(max_length=120)
	weekday = models.CharField(max_length=20, choices=Weekday.choices)
	start_time = models.TimeField()
	end_time = models.TimeField()
	room = models.ForeignKey(Room, on_delete=models.PROTECT, related_name='timetable_entries')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['weekday', 'start_time', 'course', 'section']

	def __str__(self):
		return f"{self.course} {self.section} - {self.subject} ({self.weekday})"
