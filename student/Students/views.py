from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from .models import (
	Student,
	AdmissionApplication,
	AttendanceRecord,
	ExamSchedule,
	Subject,
	ExamResult,
	ExamFormSubmission,
	ExamFormSubjectSelection,
	FeeStructure,
	FeeInvoice,
	FeePayment,
	Room,
	TimetableEntry,
)
from .forms import (
	StudentForm,
	CustomUserCreationForm,
	AdmissionApplicationForm,
	AttendanceRecordForm,
	ExamScheduleForm,
	ExamResultForm,
	FeeStructureForm,
	FeeInvoiceForm,
	FeePaymentForm,
	RoomForm,
	TimetableEntryForm,
	OnlineResultSearchForm,
	HallTicketSearchForm,
	ExamFormSubmissionForm,
)
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.cache import never_cache
from django.db.models import Q, Sum, Count, Max
import csv
import random
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import re
from urllib.parse import urlencode


@method_decorator(never_cache, name='dispatch')
class CustomLoginView(auth_views.LoginView):
	"""Login view that adds a success message after successful authentication.

	Uses the same template as before (Students/login.html) and relies on
	LOGIN_REDIRECT_URL for the post-login redirect.
	"""
	redirect_authenticated_user = True

	def form_valid(self, form):
		# Call the parent to log the user in and obtain the response/redirect
		response = super().form_valid(form)
		messages.success(self.request, 'Successfully logged in.')
		return response


class StudentListView(LoginRequiredMixin, ListView):
	model = Student
	template_name = 'Students/student_list.html'
	context_object_name = 'students'

	def get_queryset(self):
		queryset = Student.objects.all()
		search_query = self.request.GET.get('q', '').strip()
		course = self.request.GET.get('course', '').strip()
		status = self.request.GET.get('status', '').strip()

		if search_query:
			queryset = queryset.filter(
				Q(first_name__icontains=search_query)
				| Q(last_name__icontains=search_query)
				| Q(email__icontains=search_query)
				| Q(course__icontains=search_query)
			)

		if course:
			queryset = queryset.filter(course=course)

		if status == 'active':
			queryset = queryset.filter(is_active=True)
		elif status == 'inactive':
			queryset = queryset.filter(is_active=False)

		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['filter_q'] = self.request.GET.get('q', '').strip()
		context['filter_course'] = self.request.GET.get('course', '').strip()
		context['filter_status'] = self.request.GET.get('status', '').strip()
		context['course_options'] = (
			Student.objects.order_by('course')
			.values_list('course', flat=True)
			.distinct()
		)
		context['results_count'] = context['students'].count()
		return context


class StudentDetailView(LoginRequiredMixin, DetailView):
	model = Student
	template_name = 'Students/student_detail.html'


class StudentCreateView(LoginRequiredMixin, CreateView):
	model = Student
	form_class = StudentForm
	template_name = 'Students/student_form.html'
	success_url = reverse_lazy('students:list')

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, 'Student added successfully.')
		return response


class StudentUpdateView(LoginRequiredMixin, UpdateView):
	model = Student
	form_class = StudentForm
	template_name = 'Students/student_form.html'
	success_url = reverse_lazy('students:list')

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, 'Student updated successfully.')
		return response


class StudentDeleteView(LoginRequiredMixin, DeleteView):
	model = Student
	template_name = 'Students/student_confirm_delete.html'
	success_url = reverse_lazy('students:list')

	def delete(self, request, *args, **kwargs):
		obj = self.get_object()
		messages.success(request, f'Student "{obj}" deleted successfully.')
		return super().delete(request, *args, **kwargs)


@never_cache
def logout_view(request):
	"""Log out the user, add a popup message, and redirect to home page."""
	logout(request)
	messages.success(request, 'You have been logged out successfully.')
	return redirect('students:home')


class DashboardView(LoginRequiredMixin, ListView):
	"""Dashboard showing student details after login.
	
	For admin users: shows all students with stats.
	For regular users: shows a welcome message.
	"""
	model = Student
	template_name = 'Students/dashboard.html'
	context_object_name = 'students'

	def get_queryset(self):
		# Show all students for admin, empty for regular users
		if self.request.user.is_staff:
			return Student.objects.all()
		return Student.objects.none()

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['is_admin'] = self.request.user.is_staff
		context['total_students'] = Student.objects.count()
		context['active_students'] = Student.objects.filter(is_active=True).count()
		context['inactive_students'] = context['total_students'] - context['active_students']
		context['active_rate'] = (
			round((context['active_students'] / context['total_students']) * 100, 1)
			if context['total_students'] else 0
		)

		today = timezone.localdate()
		context['today'] = today
		context['application_count'] = AdmissionApplication.objects.count()
		context['attendance_today_count'] = AttendanceRecord.objects.filter(attendance_date=today).count()
		context['present_today_count'] = AttendanceRecord.objects.filter(
			attendance_date=today,
			status=AttendanceRecord.Status.PRESENT,
		).count()
		context['upcoming_exam_count'] = ExamSchedule.objects.filter(exam_date__gte=today).count()
		context['pending_invoice_count'] = FeeInvoice.objects.filter(
			status__in=[FeeInvoice.Status.PENDING, FeeInvoice.Status.PARTIAL, FeeInvoice.Status.OVERDUE]
		).count()
		context['overdue_invoice_count'] = FeeInvoice.objects.filter(status=FeeInvoice.Status.OVERDUE).count()
		context['recent_admissions'] = AdmissionApplication.objects.select_related('student').order_by(
			'-application_date', '-created_at'
		)[:5]
		context['upcoming_exams'] = ExamSchedule.objects.filter(exam_date__gte=today).order_by(
			'exam_date', 'start_time'
		)[:5]
		context['recent_payments'] = FeePayment.objects.select_related(
			'invoice', 'invoice__student'
		).order_by('-payment_date', '-created_at')[:5]

		invoice_totals = FeeInvoice.objects.aggregate(
			total_amount=Sum('total_amount'),
			total_discount=Sum('discount_amount'),
			total_scholarship=Sum('scholarship_amount'),
		)
		total_amount = invoice_totals['total_amount'] or 0
		total_discount = invoice_totals['total_discount'] or 0
		total_scholarship = invoice_totals['total_scholarship'] or 0
		total_payable = total_amount - total_discount - total_scholarship
		total_collected = FeePayment.objects.aggregate(total=Sum('amount'))['total'] or 0
		total_outstanding = total_payable - total_collected
		context['total_payable'] = total_payable if total_payable > 0 else 0
		context['total_collected'] = total_collected if total_collected > 0 else 0
		context['total_outstanding'] = total_outstanding if total_outstanding > 0 else 0
		context['collection_rate'] = (
			round((context['total_collected'] / context['total_payable']) * 100, 1)
			if context['total_payable'] else 0
		)
		module_groups = [
			{
				"title": "Student Information Management",
				"icon": "SI",
				"summary": "Core profile lifecycle from admission to identity and records.",
				"features": [
					"Student registration and enrollment",
					"Personal details: name, DOB, contact information, address",
					"Guardian and parent information",
					"Document uploads: ID, transcripts, certificates",
					"Automatic student ID generation",
				],
			},
			{
				"title": "Admission and Enrollment Management",
				"icon": "AE",
				"summary": "Application intake, tracking, and enrollment decisions.",
				"features": [
					"Online admission forms",
					"Application status tracking",
					"Merit list generation",
					"Course and program assignment",
					"Enrollment status management",
				],
			},
			{
				"title": "Course and Class Management",
				"icon": "CC",
				"summary": "Academic structure and scheduling foundations.",
				"features": [
					"Course creation and assignment",
					"Class and section management",
					"Subject allocation",
					"Academic calendar management",
					"Credit hour management",
				],
			},
			{
				"title": "Attendance Management",
				"icon": "AT",
				"summary": "Daily tracking with reporting and alerting.",
				"features": [
					"Daily attendance recording",
					"Biometric and RFID integration (optional)",
					"Attendance reports: daily, monthly, term-wise",
					"Absence alerts for parents and students",
				],
			},
			{
				"title": "Examination and Grading",
				"icon": "EG",
				"summary": "Assessments, marks processing, and transcripts.",
				"features": [
					"Exam scheduling",
					"Marks entry and grade calculation",
					"GPA and CGPA calculation",
					"Report card generation",
					"Transcript generation",
				],
			},
			{
				"title": "Fee and Financial Management",
				"icon": "FF",
				"summary": "Finance workflows with payments and records.",
				"features": [
					"Fee structure setup",
					"Online fee payment integration",
					"Payment tracking",
					"Invoice and receipt generation",
					"Scholarship and discount management",
				],
			},
			{
				"title": "Timetable Management",
				"icon": "TM",
				"summary": "Conflict-free schedules for classes, faculty, and rooms.",
				"features": [
					"Class timetable generation",
					"Faculty timetable",
					"Room allocation",
					"Conflict detection",
				],
			},
			{
				"title": "Communication System",
				"icon": "CM",
				"summary": "Real-time communication for all stakeholders.",
				"features": [
					"SMS and email notifications",
					"Announcements and circulars",
					"Parent-teacher communication portal",
					"In-app messaging",
				],
			},
			{
				"title": "Teacher and Staff Management",
				"icon": "TS",
				"summary": "Staff operations and performance oversight.",
				"features": [
					"Staff profiles",
					"Payroll management",
					"Subject assignment",
					"Performance tracking",
				],
			},
			{
				"title": "Reports and Analytics",
				"icon": "RA",
				"summary": "Decision-making intelligence and KPI visibility.",
				"features": [
					"Student performance reports",
					"Attendance analytics",
					"Financial reports",
					"Custom report generation",
					"Dashboard with KPIs",
				],
			},
			{
				"title": "Library Management",
				"icon": "LB",
				"summary": "Optional library operations that are commonly needed.",
				"features": [
					"Book catalog management",
					"Issue and return tracking",
					"Fine calculation",
				],
			},
			{
				"title": "User Roles and Access Control",
				"icon": "AC",
				"summary": "Secure role-based access for all portals.",
				"features": [
					"Admin dashboard",
					"Teacher portal",
					"Student portal",
					"Parent portal",
					"Role-based permissions",
				],
			},
			{
				"title": "Advanced and Modern Features",
				"icon": "AI",
				"summary": "Future-ready capabilities for scale and innovation.",
				"features": [
					"Mobile app integration",
					"Learning Management System integration",
					"AI-based performance insights",
					"Online examination system",
					"Hostel and transport management",
					"Alumni management",
				],
			},
		]
		context['module_groups'] = module_groups
		context['total_modules'] = len(module_groups)
		return context


class StaffRequiredMixin(LoginRequiredMixin):
	"""
	Workflow access mixin.
	Kept class name for existing views, but allows any authenticated user
	to open workflow pages (admission, attendance, exams, fees, etc.).
	"""
	pass


def _sync_invoice_status(invoice):
	if invoice.due_amount <= 0:
		invoice.status = FeeInvoice.Status.PAID
	elif invoice.paid_amount > 0:
		invoice.status = FeeInvoice.Status.PARTIAL
	elif invoice.due_date < timezone.localdate():
		invoice.status = FeeInvoice.Status.OVERDUE
	else:
		invoice.status = FeeInvoice.Status.PENDING
	invoice.save(update_fields=['status'])


class WorkflowHubView(StaffRequiredMixin, TemplateView):
	template_name = 'Students/workflows/hub.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['application_count'] = AdmissionApplication.objects.count()
		context['attendance_count'] = AttendanceRecord.objects.count()
		context['exam_count'] = ExamSchedule.objects.count()
		context['invoice_count'] = FeeInvoice.objects.count()
		context['timetable_count'] = TimetableEntry.objects.count()
		return context


class WorkflowCompleteFlowView(StaffRequiredMixin, TemplateView):
	template_name = 'Students/workflows/complete_flow.html'


class AdmissionApplicationListView(StaffRequiredMixin, ListView):
	model = AdmissionApplication
	template_name = 'Students/workflows/admission_list.html'
	context_object_name = 'applications'
	paginate_by = 20

	def get_queryset(self):
		return AdmissionApplication.objects.select_related('student').order_by('-application_date', '-created_at')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['form'] = kwargs.get('form') or AdmissionApplicationForm()
		return context

	def post(self, request, *args, **kwargs):
		post_data = request.POST.copy()

		manual_first_name = request.POST.get('manual_first_name', '').strip()
		manual_last_name = request.POST.get('manual_last_name', '').strip()
		manual_email = request.POST.get('manual_email', '').strip().lower()
		manual_course = request.POST.get('manual_course', '').strip()
		manual_enrollment_date = request.POST.get('manual_enrollment_date', '').strip()
		manual_fields_used = any([
			manual_first_name,
			manual_last_name,
			manual_email,
			manual_course,
			manual_enrollment_date,
		])

		if not post_data.get('student') and manual_fields_used:
			manual_errors = []
			if not manual_first_name:
				manual_errors.append('Manual student first name is required.')
			if not manual_last_name:
				manual_errors.append('Manual student last name is required.')
			if not manual_email:
				manual_errors.append('Manual student email is required.')
			if not manual_course:
				manual_errors.append('Manual student course is required.')
			if not manual_enrollment_date:
				manual_errors.append('Manual enrollment date is required.')

			parsed_enrollment_date = None
			if manual_enrollment_date:
				try:
					parsed_enrollment_date = date.fromisoformat(manual_enrollment_date)
				except ValueError:
					manual_errors.append('Manual enrollment date format must be YYYY-MM-DD.')

			if manual_email and Student.objects.filter(email=manual_email).exists():
				manual_errors.append('A student with this email already exists. Select from Student Record.')

			if not manual_errors:
				new_student = Student.objects.create(
					first_name=manual_first_name,
					last_name=manual_last_name,
					email=manual_email,
					enrollment_date=parsed_enrollment_date,
					course=manual_course,
					is_active=True,
				)
				post_data['student'] = str(new_student.pk)

		form = AdmissionApplicationForm(post_data)
		if request.POST.get('declaration') != 'yes':
			form.add_error(None, 'Please accept the declaration before submitting the admission form.')
		if not post_data.get('student'):
			form.add_error('student', 'Select Student Record or fill manual student details.')
		if not post_data.get('student') and manual_fields_used:
			if not manual_first_name:
				form.add_error(None, 'Manual student first name is required.')
			if not manual_last_name:
				form.add_error(None, 'Manual student last name is required.')
			if not manual_email:
				form.add_error(None, 'Manual student email is required.')
			if not manual_course:
				form.add_error(None, 'Manual student course is required.')
			if not manual_enrollment_date:
				form.add_error(None, 'Manual enrollment date is required.')
			if manual_email and Student.objects.filter(email=manual_email).exists():
				form.add_error(None, 'Manual student email already exists. Use Student Record dropdown.')
		if form.is_valid():
			form.save()
			messages.success(request, 'Admission application created and added to the table.')
			return redirect('students:admission_list')
		self.object_list = self.get_queryset()
		context = self.get_context_data(form=form)
		return self.render_to_response(context)


class AdmissionApplicationCreateView(StaffRequiredMixin, CreateView):
	model = AdmissionApplication
	form_class = AdmissionApplicationForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:admission_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'New Admission Application'
		context['back_url'] = reverse_lazy('students:admission_list')
		return context

	def form_valid(self, form):
		messages.success(self.request, 'Admission application created.')
		return super().form_valid(form)


class AttendanceRecordListView(StaffRequiredMixin, ListView):
	model = AttendanceRecord
	template_name = 'Students/workflows/attendance_list.html'
	context_object_name = 'records'
	paginate_by = 30


class AttendanceRecordCreateView(StaffRequiredMixin, CreateView):
	model = AttendanceRecord
	form_class = AttendanceRecordForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:attendance_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'Record Attendance'
		context['back_url'] = reverse_lazy('students:attendance_list')
		return context

	def form_valid(self, form):
		messages.success(self.request, 'Attendance record saved.')
		return super().form_valid(form)


class ExamScheduleListView(StaffRequiredMixin, ListView):
	model = ExamSchedule
	template_name = 'Students/workflows/exam_schedule_list.html'
	context_object_name = 'exams'
	paginate_by = 20


class ExamScheduleCreateView(StaffRequiredMixin, CreateView):
	model = ExamSchedule
	form_class = ExamScheduleForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:exam_schedule_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'Schedule Exam'
		context['back_url'] = reverse_lazy('students:exam_schedule_list')
		return context

	def form_valid(self, form):
		messages.success(self.request, 'Exam schedule created.')
		return super().form_valid(form)


class ExamResultListView(StaffRequiredMixin, ListView):
	model = ExamResult
	template_name = 'Students/workflows/exam_result_list.html'
	context_object_name = 'results'
	paginate_by = 30

	def get_queryset(self):
		return ExamResult.objects.select_related('student', 'exam')


class ExamResultCreateView(StaffRequiredMixin, CreateView):
	model = ExamResult
	form_class = ExamResultForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:exam_result_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'Add Exam Result'
		context['back_url'] = reverse_lazy('students:exam_result_list')
		return context

	def form_valid(self, form):
		messages.success(self.request, 'Exam result saved.')
		return super().form_valid(form)


class FeeStructureListView(StaffRequiredMixin, ListView):
	model = FeeStructure
	template_name = 'Students/workflows/fee_structure_list.html'
	context_object_name = 'structures'
	paginate_by = 20

	def _course_fee_breakdown(self, course, total_amount):
		"""Return admission + semester-wise fee split with course-specific values."""
		course_key = (course or '').strip().upper()
		presets = {
			'MCA': [Decimal('12000.00'), Decimal('36000.00'), Decimal('34000.00'), Decimal('33000.00'), Decimal('33000.00')],
			'MBA': [Decimal('15000.00'), Decimal('42000.00'), Decimal('39000.00'), Decimal('37000.00'), Decimal('37000.00')],
			'BBA': [Decimal('9000.00'), Decimal('28000.00'), Decimal('26000.00'), Decimal('25000.00'), Decimal('25000.00')],
			'BCA': [Decimal('10000.00'), Decimal('30000.00'), Decimal('28000.00'), Decimal('27000.00'), Decimal('27000.00')],
			'CA': [Decimal('18000.00'), Decimal('45000.00'), Decimal('42000.00'), Decimal('40000.00'), Decimal('40000.00')],
		}
		if course_key in presets:
			return presets[course_key]

		total = total_amount or Decimal('0.00')
		admission = (total * Decimal('0.10')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
		remaining = total - admission
		sem = (remaining / Decimal('4')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
		sem1 = sem2 = sem3 = sem
		sem4 = remaining - (sem1 + sem2 + sem3)
		return [admission, sem1, sem2, sem3, sem4]

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		display_structures = []
		for structure in context['structures']:
			admission_fee, first_sem, second_sem, third_sem, fourth_sem = self._course_fee_breakdown(
				structure.course, structure.total_amount
			)
			exam_fee = structure.total_amount - admission_fee
			display_structures.append({
				'structure': structure,
				'admission_fee': admission_fee,


				'exam_fee': exam_fee,
				'first_sem': first_sem,
				'second_sem': second_sem,
				'third_sem': third_sem,
				'fourth_sem': fourth_sem,
			})
		context['display_structures'] = display_structures
		return context


class FeeStructureCreateView(StaffRequiredMixin, CreateView):
	model = FeeStructure
	form_class = FeeStructureForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:fee_structure_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'New Fee Structure'
		context['back_url'] = reverse_lazy('students:fee_structure_list')
		return context

	def form_valid(self, form):
		messages.success(self.request, 'Fee structure created.')
		return super().form_valid(form)


class FeeInvoiceListView(StaffRequiredMixin, ListView):
	model = FeeInvoice
	template_name = 'Students/workflows/fee_invoice_list.html'
	context_object_name = 'invoices'
	paginate_by = 20


class FeeInvoiceCreateView(StaffRequiredMixin, CreateView):
	model = FeeInvoice
	form_class = FeeInvoiceForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:fee_invoice_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'Generate Fee Invoice'
		context['back_url'] = reverse_lazy('students:fee_invoice_list')
		return context

	def form_valid(self, form):
		response = super().form_valid(form)
		_sync_invoice_status(self.object)
		messages.success(self.request, 'Fee invoice generated.')
		return response


class FeePaymentListView(StaffRequiredMixin, ListView):
	model = FeePayment
	template_name = 'Students/workflows/fee_payment_list.html'
	context_object_name = 'payments'
	paginate_by = 30


class FeePaymentCreateView(StaffRequiredMixin, CreateView):
	model = FeePayment
	form_class = FeePaymentForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:fee_payment_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'Record Fee Payment'
		context['back_url'] = reverse_lazy('students:fee_payment_list')
		return context

	def form_valid(self, form):
		response = super().form_valid(form)
		_sync_invoice_status(self.object.invoice)
		messages.success(self.request, 'Payment recorded and invoice status updated.')
		return response


class RoomListView(StaffRequiredMixin, ListView):
	model = Room
	template_name = 'Students/workflows/room_list.html'
	context_object_name = 'rooms'
	paginate_by = 30


class RoomCreateView(StaffRequiredMixin, CreateView):
	model = Room
	form_class = RoomForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:room_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'Add Room'
		context['back_url'] = reverse_lazy('students:room_list')
		return context

	def form_valid(self, form):
		messages.success(self.request, 'Room created.')
		return super().form_valid(form)


class TimetableEntryListView(StaffRequiredMixin, ListView):
	model = TimetableEntry
	template_name = 'Students/workflows/timetable_list.html'
	context_object_name = 'entries'
	paginate_by = 30


class TimetableEntryCreateView(StaffRequiredMixin, CreateView):
	model = TimetableEntry
	form_class = TimetableEntryForm
	template_name = 'Students/workflows/form.html'
	success_url = reverse_lazy('students:timetable_list')

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['page_title'] = 'Create Timetable Entry'
		context['back_url'] = reverse_lazy('students:timetable_list')
		return context

	def form_valid(self, form):
		messages.success(self.request, 'Timetable entry created.')
		return super().form_valid(form)


class HomePageView(LoginRequiredMixin, TemplateView):
	"""Home page view that displays features and call-to-action."""
	template_name = 'Students/home.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['total_students'] = Student.objects.count()
		return context


class AboutPageView(TemplateView):
	"""About page view displaying system information."""
	template_name = 'Students/about.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['total_students'] = Student.objects.count()
		return context


def _college_site_context():
	return {
		'college_name': 'Global Institute of Technology and Management',
		'tagline': 'Learning Today, Leading Tomorrow',
		'hero_stats': [
			{'label': 'Students', 'value': '6,500+'},
			{'label': 'Faculty', 'value': '320+'},
			{'label': 'Programs', 'value': '45+'},
			{'label': 'Placements', 'value': '94%'},
		],
		'programs': [
			{'name': 'BCA', 'duration': '3 Years', 'level': 'Undergraduate'},
			{'name': 'BBA', 'duration': '3 Years', 'level': 'Undergraduate'},
			{'name': 'MBA', 'duration': '2 Years', 'level': 'Postgraduate'},
			{'name': 'MCA', 'duration': '2 Years', 'level': 'Postgraduate'},
			{'name': 'B.Tech CSE', 'duration': '4 Years', 'level': 'Undergraduate'},
			{'name': 'B.Com', 'duration': '3 Years', 'level': 'Undergraduate'},
		],
		'departments': [
			'Computer Science',
			'Management Studies',
			'Commerce and Finance',
			'Humanities and Social Sciences',
			'Basic Sciences',
			'Training and Placement',
		],
		'facilities': [
			'Digital Library and e-Journals',
			'Smart Classrooms',
			'Computer Labs with High-Speed Internet',
			'Hostel and Transport Services',
			'Sports Complex and Gymnasium',
			'Innovation and Startup Cell',
		],
		'notices': [
			'Admissions Open for 2026-27 Session',
			'Mid-Term Examination Schedule Published',
			'Scholarship Applications Close on 30 April 2026',
			'Campus Placement Drive Starts from 15 May 2026',
		],
		'events': [
			{'name': 'Annual Tech Fest', 'date': 'April 18, 2026'},
			{'name': 'Industry Connect Seminar', 'date': 'May 05, 2026'},
			{'name': 'Inter-College Sports Meet', 'date': 'June 10, 2026'},
		],
		'placement_partners': [
			'TCS',
			'Infosys',
			'Wipro',
			'Accenture',
			'Cognizant',
			'HCL',
		],
		'contact': {
			'address': 'Knowledge Park Road, Sector 12, New Delhi, India',
			'email': 'admissions@gitm.edu',
			'phone': '+91 98765 43210',
		},
	}


class CollegeWebsiteHomeView(TemplateView):
	template_name = 'Students/college/home.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		return context


class CollegeCoursesView(TemplateView):
	template_name = 'Students/college/courses.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		return context


class CollegeAdmissionsView(TemplateView):
	template_name = 'Students/college/admissions.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		return context


class CollegeDepartmentsView(TemplateView):
	template_name = 'Students/college/departments.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		return context


class CollegeFacultyView(TemplateView):
	template_name = 'Students/college/faculty.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		context['faculty_members'] = [
			{'name': 'Dr. Ananya Sharma', 'designation': 'Professor, Computer Science'},
			{'name': 'Dr. Rohan Mehta', 'designation': 'Professor, Management Studies'},
			{'name': 'Prof. Neha Verma', 'designation': 'Associate Professor, Commerce'},
			{'name': 'Prof. Arjun Rao', 'designation': 'Assistant Professor, Mathematics'},
		]
		return context


class CollegeContactView(TemplateView):
	template_name = 'Students/college/contact.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		return context


class CollegeExamStudentLoginView(TemplateView):
	template_name = 'Students/college/exam_student_login.html'

	def _generate_captcha(self):
		return ''.join(str(random.randint(0, 9)) for _ in range(5))

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		context['lookup_error'] = kwargs.get('lookup_error')
		context['support_phone'] = kwargs.get('support_phone', '+91 020-71533633')
		context['support_email'] = kwargs.get('support_email', 'examsupport@pun.unipune.ac.in')
		context['captcha_code'] = kwargs.get('captcha_code') or self._generate_captcha()
		return context

	def post(self, request, *args, **kwargs):
		login_by = request.POST.get('login_by', '').strip()
		password = request.POST.get('password', '').strip()
		mobile_number = request.POST.get('mobile_number', '').strip()
		captcha_text = request.POST.get('captcha_text', '').strip()
		captcha_expected = request.POST.get('captcha_expected', '').strip()
		if not login_by or not password or not mobile_number or not captcha_text:
			context = self.get_context_data(
				lookup_error='Please fill Login By, Password, Mobile Number, and Captcha to continue.',
				captcha_code=self._generate_captcha(),
			)
			return self.render_to_response(context)
		if captcha_text != captcha_expected:
			context = self.get_context_data(
				lookup_error='Captcha text is incorrect. Please try again.',
				captcha_code=self._generate_captcha(),
			)
			return self.render_to_response(context)
		return redirect('students:college_exam_student_dashboard')


class CollegeExamStudentDashboardView(TemplateView):
	template_name = 'Students/college/exam_student_dashboard.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		context['demo_rows'] = [
			{
				'learning_mode': 'Regular',
				'prn': '2032400466',
				'eligibility': '12024224520',
				'course_name': 'Master of Computer Application (M.C.A.)',
				'pattern_name': 'MCA(MANAGEMENT)2024 Credit Pattern',
				'college_puncode': 'IMMA016370',
				'college_name': 'Institute of Management Studies, Career Development & Research',
				'student_name': 'KARANJKAR SOURABH VIJAYKUMAR',
				'mother_name': 'KARANJKAR NILIMA VIJAYKUMAR',
				'profile_status': 'Profile complete.',
			},
		]
		return context


class CollegeExamPortalView(TemplateView):
	template_name = 'Students/college/exam_form_portal.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		context['support_phone'] = '020-71533633'
		context['support_email'] = 'examsupport@pun.unipune.ac.in'
		context['notices'] = [
			'SEF office holiday on 1st and 3rd Saturday every month.',
			'Office call working hours are 10:30 AM to 6:00 PM.',
		]
		context['rules'] = [
			'Students can fill online exam form by creating their student profile.',
			'After filling the form, submit inward request through respective college.',
			'College will inward the submitted application number.',
			'Online payment option becomes available only after inward approval.',
		]
		return context


class CollegeExamDashboardView(TemplateView):
	template_name = 'Students/college/exam_form_dashboard.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		submissions = (
			ExamFormSubmission.objects.select_related('student')
			.order_by('-submitted_at')[:10]
		)
		context['submissions'] = submissions
		return context


class CollegeExamFormView(TemplateView):
	template_name = 'Students/college/exam_form.html'

	def _default_subject_rows(self):
		return [
			{'code': 'MCA101', 'name': 'Advanced DBMS', 'internal': 'N', 'theory': 'Y', 'online': 'N', 'practical': 'N', 'oral': 'N'},
			{'code': 'MCA102', 'name': 'Data Structures and Algorithms', 'internal': 'N', 'theory': 'Y', 'online': 'N', 'practical': 'N', 'oral': 'N'},
			{'code': 'MCA103', 'name': 'Computer Networks', 'internal': 'N', 'theory': 'Y', 'online': 'N', 'practical': 'N', 'oral': 'N'},
			{'code': 'MCA104', 'name': 'Java Programming', 'internal': 'N', 'theory': 'Y', 'online': 'N', 'practical': 'N', 'oral': 'N'},
			{'code': 'MCA105', 'name': 'Project Management', 'internal': 'N', 'theory': 'Y', 'online': 'N', 'practical': 'N', 'oral': 'N'},
		]

	def _subject_rows_for_course(self, course_name):
		course = (course_name or '').strip()
		if not course:
			return self._default_subject_rows()

		# First source of truth: dedicated subject master for the course.
		subject_qs = Subject.objects.filter(course__iexact=course, is_active=True).order_by('code')
		subject_rows = [
			{'code': s.code, 'name': s.name, 'internal': 'N', 'theory': 'Y', 'online': 'N', 'practical': 'N', 'oral': 'N'}
			for s in subject_qs
		]
		if subject_rows:
			return subject_rows

		# Bootstrap subject master from exam schedules if no subject master exists yet.
		schedules = ExamSchedule.objects.filter(course__iexact=course).order_by('subject')[:12]
		for idx, schedule in enumerate(schedules, start=1):
			base_code = (schedule.subject[:8] or f"SUBJ{idx:03d}").upper().replace(' ', '')
			subject_obj, _ = Subject.objects.get_or_create(
				course=course,
				code=base_code,
				defaults={'name': schedule.subject, 'is_active': True},
			)
			if subject_obj.name != schedule.subject:
				subject_obj.name = schedule.subject
				subject_obj.save(update_fields=['name'])
			subject_rows.append({
				'code': subject_obj.code,
				'name': subject_obj.name,
				'internal': 'N',
				'theory': 'N' if schedule.exam_type == ExamSchedule.ExamType.PRACTICAL else 'Y',
				'online': 'N',
				'practical': 'Y' if schedule.exam_type == ExamSchedule.ExamType.PRACTICAL else 'N',
				'oral': 'N',
			})
		if subject_rows:
			return subject_rows

		# Final fallback defaults + seed Subject master for this course.
		default_rows = self._default_subject_rows()
		for row in default_rows:
			Subject.objects.get_or_create(
				course=course,
				code=row['code'],
				defaults={'name': row['name'], 'is_active': True},
			)
		return default_rows

	def _fee_rows(self):
		return {
			'form_fee': 30,
			'full_exam_fee': 2200,
			'statement_fee': 145,
			'cap_fee': 290,
			'late_fee': 0,
			'fine_fee': 0,
		}

	def _fee_breakdown(self, selected_subject_count, total_subject_count):
		fee_config = self._fee_rows()
		total_subject_count = max(total_subject_count, 1)
		exam_fee_per_subject = round(fee_config['full_exam_fee'] / total_subject_count, 2)
		exam_fee = round(exam_fee_per_subject * selected_subject_count, 2)
		fee_rows = [
			{'label': 'Form Fee', 'amount': fee_config['form_fee'], 'remarks': ''},
			{'label': 'Exam Fee', 'amount': exam_fee, 'remarks': f"{selected_subject_count} subject(s) x {exam_fee_per_subject}"},
			{'label': 'Statement of Marks Fee', 'amount': fee_config['statement_fee'], 'remarks': ''},
			{'label': 'CAP Fee', 'amount': fee_config['cap_fee'], 'remarks': ''},
			{'label': 'Late Fee', 'amount': fee_config['late_fee'], 'remarks': ''},
			{'label': 'Fine Fee', 'amount': fee_config['fine_fee'], 'remarks': ''},
		]
		total_fee = round(sum(row['amount'] for row in fee_rows), 2)
		return fee_rows, total_fee, exam_fee_per_subject

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		form = kwargs.get('form') or ExamFormSubmissionForm(initial={'exam_session': '2026-27', 'medium': 'English'})
		context['form'] = form
		context['submitted'] = kwargs.get('submitted', False)
		context['lookup_error'] = kwargs.get('lookup_error')
		context['student_match'] = kwargs.get('student_match')
		context['submission'] = kwargs.get('submission')

		seat_number = ''
		if hasattr(form, 'cleaned_data') and form.is_bound:
			seat_number = form.cleaned_data.get('seat_number', '') if form.is_valid() else form.data.get('seat_number', '')
		elif hasattr(form, 'initial'):
			seat_number = form.initial.get('seat_number', '')
		seat_number = (seat_number or '').strip().upper()
		student_preview = Student.objects.filter(seat_number__iexact=seat_number).first() if seat_number else None
		if not student_preview and form.is_bound:
			email = (form.data.get('email') or '').strip().lower()
			if email:
				student_preview = Student.objects.filter(email__iexact=email).first()

		course_name = ''
		if form.is_bound:
			course_name = (form.data.get('course') or '').strip()
		if not course_name and student_preview:
			course_name = student_preview.course
		subject_rows = self._subject_rows_for_course(course_name)
		selected_subject_codes = kwargs.get('selected_subject_codes')
		submission = context.get('submission')
		saved_selections = {}
		if submission:
			selection_qs = submission.subject_selections.select_related('subject')
			for sel in selection_qs:
				saved_selections[sel.subject.code] = {
					'is_selected': sel.is_selected,
					'int': sel.component_internal,
					'th': sel.component_theory,
					'onl': sel.component_online,
					'pr': sel.component_practical,
					'or': sel.component_oral,
				}
		if selected_subject_codes is None:
			if form.is_bound:
				selected_subject_codes = form.data.getlist('selected_subject_codes')
			elif saved_selections:
				selected_subject_codes = [code for code, data in saved_selections.items() if data.get('is_selected')]
			elif submission and submission.selected_subject_codes:
				selected_subject_codes = [code.strip() for code in submission.selected_subject_codes.split(',') if code.strip()]
			else:
				selected_subject_codes = [row['code'] for row in subject_rows]
		selected_subject_count = len([code for code in selected_subject_codes if code])
		component_selection = {}
		component_keys = ['int', 'th', 'onl', 'pr', 'or']
		if form.is_bound:
			for row in subject_rows:
				code = row['code']
				selected_components = set()
				for key in component_keys:
					if f"comp_{key}_{code}" in form.data:
						selected_components.add(key)
				component_selection[code] = selected_components
		else:
			for row in subject_rows:
				code = row['code']
				selected_components = set()
				if code in saved_selections:
					if saved_selections[code].get('int'):
						selected_components.add('int')
					if saved_selections[code].get('th'):
						selected_components.add('th')
					if saved_selections[code].get('onl'):
						selected_components.add('onl')
					if saved_selections[code].get('pr'):
						selected_components.add('pr')
					if saved_selections[code].get('or'):
						selected_components.add('or')
				elif row.get('internal') == 'Y':
					selected_components.add('int')
				if row.get('theory') == 'Y':
					selected_components.add('th')
				if row.get('online') == 'Y':
					selected_components.add('onl')
				if row.get('practical') == 'Y':
					selected_components.add('pr')
				if row.get('oral') == 'Y':
					selected_components.add('or')
				component_selection[code] = selected_components
		for row in subject_rows:
			selected_components = component_selection.get(row['code'], set())
			row['checked_int'] = 'int' in selected_components
			row['checked_th'] = 'th' in selected_components
			row['checked_onl'] = 'onl' in selected_components
			row['checked_pr'] = 'pr' in selected_components
			row['checked_or'] = 'or' in selected_components

		fee_rows, total_fee, exam_fee_per_subject = self._fee_breakdown(selected_subject_count, len(subject_rows))
		fee_config = self._fee_rows()
		context['student_preview'] = student_preview
		context['subject_rows'] = subject_rows
		context['selected_subject_codes'] = selected_subject_codes
		context['selected_subject_count'] = selected_subject_count
		context['total_subject_count'] = len(subject_rows)
		context['fee_rows'] = fee_rows
		context['total_fee'] = total_fee
		context['exam_fee_per_subject'] = exam_fee_per_subject
		context['fee_config'] = fee_config
		context['print_date'] = timezone.localtime()
		return context

	def post(self, request, *args, **kwargs):
		form = ExamFormSubmissionForm(request.POST)
		if form.is_valid():
			seat_number = form.cleaned_data['seat_number']
			date_of_birth = form.cleaned_data.get('date_of_birth')
			first_name = form.cleaned_data['first_name']
			last_name = form.cleaned_data['last_name']
			email = form.cleaned_data['email'].strip().lower()
			course = form.cleaned_data['course'].strip()
			mother_name = form.cleaned_data.get('mother_name', '').strip()
			father_name = form.cleaned_data.get('father_name', '').strip()
			parent_name = form.cleaned_data.get('parent_name', '').strip()
			address = form.cleaned_data.get('address', '').strip()
			mobile_number = form.cleaned_data.get('mobile_number', '').strip()
			gender = form.cleaned_data.get('gender', '').strip()
			category = form.cleaned_data.get('category', '').strip()
			medium = form.cleaned_data.get('medium', '').strip() or 'English'
			semester = form.cleaned_data['semester']
			exam_session = form.cleaned_data['exam_session']
			selected_subject_codes = [code.strip().upper() for code in request.POST.getlist('selected_subject_codes') if code.strip()]
			course_subject_rows = self._subject_rows_for_course(course)

			student_match = None
			if seat_number:
				student_match = Student.objects.filter(seat_number__iexact=seat_number).first()
				if not student_match:
					context = self.get_context_data(
						form=form,
						submitted=True,
						lookup_error='Seat number not found. Leave seat number blank to auto-generate, or enter a valid existing seat number.',
					)
					return self.render_to_response(context)
			else:
				student_match = Student.objects.filter(email__iexact=email).first()

			existing_dob = student_match.date_of_birth if student_match else None
			if not student_match:
				student_match = Student(
					first_name=first_name,
					last_name=last_name,
					email=email,
					enrollment_date=timezone.localdate(),
					course=course,
					is_active=True,
				)
			email_owner = Student.objects.filter(email__iexact=email).exclude(pk=student_match.pk).first() if student_match.pk else Student.objects.filter(email__iexact=email).first()
			if email_owner:
				context = self.get_context_data(
					form=form,
					submitted=True,
					lookup_error='This email is already used by another student record. Use a different email or matching seat number.',
				)
				return self.render_to_response(context)

			student_match.first_name = first_name
			student_match.last_name = last_name
			student_match.email = email
			student_match.course = course
			student_match.date_of_birth = date_of_birth
			student_match.mother_name = mother_name
			student_match.father_name = father_name
			student_match.parent_name = parent_name
			if seat_number:
				student_match.seat_number = seat_number
			student_match.save()

			if date_of_birth and existing_dob and existing_dob != date_of_birth:
				context = self.get_context_data(
					form=form,
					submitted=True,
					lookup_error='DOB verification failed. Please enter the correct date of birth.',
				)
				return self.render_to_response(context)

			valid_subject_codes = {row['code'] for row in course_subject_rows}
			selected_subject_codes = [code for code in selected_subject_codes if code in valid_subject_codes]
			if not selected_subject_codes:
				context = self.get_context_data(
					form=form,
					submitted=True,
					student_match=student_match,
					lookup_error='Please tick at least one subject in Applied Subject Information.',
					selected_subject_codes=selected_subject_codes,
				)
				return self.render_to_response(context)

			submission, _ = ExamFormSubmission.objects.update_or_create(
				student=student_match,
				semester=semester,
				exam_session=exam_session,
				defaults={
					'address': address,
					'mobile_number': mobile_number,
					'gender': gender,
					'category': category,
					'medium': medium,
					'selected_subject_codes': ','.join(selected_subject_codes),
					'declaration_accepted': form.cleaned_data['declaration'],
				},
			)
			component_map = {}
			for row in course_subject_rows:
				code = row['code']
				component_map[code] = {
					'int': f"comp_int_{code}" in request.POST,
					'th': f"comp_th_{code}" in request.POST,
					'onl': f"comp_onl_{code}" in request.POST,
					'pr': f"comp_pr_{code}" in request.POST,
					'or': f"comp_or_{code}" in request.POST,
				}

			# Keep per-subject component selections in normalized backend storage.
			kept_subject_ids = []
			for row in course_subject_rows:
				code = row['code']
				subject_obj, _ = Subject.objects.get_or_create(
					course=course,
					code=code,
					defaults={'name': row['name'], 'is_active': True},
				)
				kept_subject_ids.append(subject_obj.id)
				components = component_map.get(code, {})
				is_selected = code in selected_subject_codes
				if is_selected and not any(components.values()):
					components['th'] = True
				ExamFormSubjectSelection.objects.update_or_create(
					submission=submission,
					subject=subject_obj,
					defaults={
						'is_selected': is_selected,
						'component_internal': bool(components.get('int')),
						'component_theory': bool(components.get('th')),
						'component_online': bool(components.get('onl')),
						'component_practical': bool(components.get('pr')),
						'component_oral': bool(components.get('or')),
					},
				)
			ExamFormSubjectSelection.objects.filter(submission=submission).exclude(subject_id__in=kept_subject_ids).delete()

			query = urlencode({
				'seat_number': student_match.seat_number,
				'exam_session': submission.exam_session,
				'semester': submission.semester,
				'from_exam_form': '1',
			})
			return redirect(f"{reverse('students:college_hall_ticket')}?{query}")

		context = self.get_context_data(form=form, submitted=True)
		return self.render_to_response(context)


class CollegeOnlineResultView(TemplateView):
	template_name = 'Students/college/results.html'

	def _infer_semester(self, exam_title):
		title = exam_title or ''
		match = re.search(r'(?:SEM(?:ESTER)?)[\s\-\.:]*([IVX]+|\d+)', title, flags=re.IGNORECASE)
		if match:
			return f"Semester {match.group(1).upper()}"
		return 'Semester -'

	def _declaration_rows(self):
		return (
			ExamSchedule.objects.filter(results__isnull=False)
			.values('course', 'subject')
			.annotate(
				result_declare_date=Max('exam_date'),
				total_students=Count('results'),
			)
			.order_by('course', 'subject')
		)

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		selected_course = kwargs.get('selected_course')
		if selected_course is None:
			selected_course = self.request.GET.get('course', '').strip()
		context['selected_course'] = selected_course
		context['declaration_rows'] = self._declaration_rows()
		context['form'] = kwargs.get('form') or OnlineResultSearchForm()
		context['searched'] = kwargs.get('searched', False)
		context['results'] = kwargs.get('results')
		context['student_match'] = kwargs.get('student_match')
		context['lookup_error'] = kwargs.get('lookup_error')
		context['print_ready'] = kwargs.get('print_ready', False)
		return context

	def post(self, request, *args, **kwargs):
		selected_course = request.POST.get('selected_course', '').strip()
		form = OnlineResultSearchForm(request.POST)
		if not selected_course:
			context = self.get_context_data(
				form=form,
				searched=True,
				selected_course=selected_course,
				lookup_error='Please select a course from Result Declaration table first.',
			)
			return self.render_to_response(context)

		if form.is_valid():
			seat_number = form.cleaned_data['seat_number']
			seat_student = Student.objects.filter(seat_number__iexact=seat_number).first()
			if not seat_student:
				context = self.get_context_data(
					form=form,
					searched=True,
					selected_course=selected_course,
					lookup_error='Seat number not found. Please check the seat number.',
				)
				return self.render_to_response(context)

			student_match = seat_student

			results_qs = ExamResult.objects.select_related('exam').filter(
				student=student_match,
				exam__course__iexact=selected_course,
			).order_by(
				'-exam__exam_date', 'exam__start_time'
			)
			results = []
			for r in results_qs:
				results.append({
					'exam_title': r.exam.title,
					'subject': r.exam.subject,
					'course': r.exam.course,
					'exam_date': r.exam.exam_date,
					'marks_obtained': r.marks_obtained,
					'grade': r.grade,
					'semester': self._infer_semester(r.exam.title),
				})
			context = self.get_context_data(
				form=form,
				searched=True,
				results=results,
				student_match=student_match,
				selected_course=selected_course,
				print_ready=bool(results),
			)
			return self.render_to_response(context)

		context = self.get_context_data(form=form, searched=True, selected_course=selected_course)
		return self.render_to_response(context)



class CollegeHallTicketView(TemplateView):
	template_name = 'Students/college/hall_ticket.html'

	def _exam_schedules_for_student(self, student, exam_form_submission=None):
		exam_schedules = list(
			ExamSchedule.objects.filter(course__iexact=student.course).order_by('exam_date', 'start_time')
		)
		if exam_schedules:
			return exam_schedules

		# Fallback 1: use structured subject selections from exam form.
		if not exam_form_submission:
			return []
		selection_qs = exam_form_submission.subject_selections.select_related('subject').filter(is_selected=True)
		if selection_qs.exists():
			fallback_rows = []
			for sel in selection_qs:
				fallback_rows.append({
					'subject': sel.subject.name,
					'title': f"{sel.subject.code} - As per Exam Form",
					'exam_date': None,
					'start_time': None,
					'end_time': None,
					'room': '',
				})
			return fallback_rows

		# Fallback 2: backward compatibility for old text-based submissions.
		if not exam_form_submission.selected_subject_codes:
			return []
		codes = [
			code.strip().upper()
			for code in exam_form_submission.selected_subject_codes.split(',')
			if code.strip()
		]
		if not codes:
			return []

		fallback_rows = []
		for code in codes:
			subject_obj = Subject.objects.filter(course__iexact=student.course, code=code).first()
			subject_name = subject_obj.name if subject_obj else code
			fallback_rows.append({
				'subject': subject_name,
				'title': f"{code} - As per Exam Form",
				'exam_date': None,
				'start_time': None,
				'end_time': None,
				'room': '',
			})
		return fallback_rows

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context.update(_college_site_context())
		context['form'] = kwargs.get('form') or HallTicketSearchForm()
		context['searched'] = kwargs.get('searched', False)
		context['lookup_error'] = kwargs.get('lookup_error')
		context['lookup_warning'] = kwargs.get('lookup_warning')
		context['flow_message'] = kwargs.get('flow_message')
		context['student_match'] = kwargs.get('student_match')
		context['exam_schedules'] = kwargs.get('exam_schedules')
		context['exam_form_submission'] = kwargs.get('exam_form_submission')
		context['hall_instructions'] = [
			'Carry a printed hall ticket and valid photo ID to the exam center.',
			'Reach the exam center at least 30 minutes before exam start time.',
			'Electronic gadgets and unfair means are strictly prohibited.',
			'Verify seat number, subject, and exam center before entering the hall.',
		]
		context['generated_on'] = timezone.localdate()
		return context

	def get(self, request, *args, **kwargs):
		seat_number = request.GET.get('seat_number', '').strip().upper()
		if seat_number:
			student_match = Student.objects.filter(seat_number__iexact=seat_number).first()
			if not student_match:
				context = self.get_context_data(
					form=HallTicketSearchForm(initial={'seat_number': seat_number}),
					searched=True,
					lookup_error='Seat number not found. Enter the exact seat number from UniPune hall ticket (example: S01423). If it still fails, contact college admin.',
				)
				return self.render_to_response(context)

			exam_form_submission = ExamFormSubmission.objects.filter(student=student_match).order_by('-submitted_at').first()
			exam_session = request.GET.get('exam_session', '').strip()
			semester = request.GET.get('semester', '').strip()
			if exam_session or semester:
				qs = ExamFormSubmission.objects.filter(student=student_match)
				if exam_session:
					qs = qs.filter(exam_session=exam_session)
				if semester:
					qs = qs.filter(semester=semester)
				exam_form_submission = qs.order_by('-submitted_at').first() or exam_form_submission
			exam_schedules = self._exam_schedules_for_student(student_match, exam_form_submission)

			flow_message = None
			if request.GET.get('from_exam_form') == '1':
				flow_message = 'Exam form submitted successfully. Hall ticket has been generated from your exam form details.'

			context = self.get_context_data(
				form=HallTicketSearchForm(initial={'seat_number': seat_number}),
				searched=True,
				student_match=student_match,
				exam_schedules=exam_schedules,
				exam_form_submission=exam_form_submission,
				flow_message=flow_message,
			)
			return self.render_to_response(context)
		return super().get(request, *args, **kwargs)

	def post(self, request, *args, **kwargs):
		form = HallTicketSearchForm(request.POST)
		if form.is_valid():
			seat_number = form.cleaned_data['seat_number']
			date_of_birth = form.cleaned_data.get('date_of_birth')
			student_match = Student.objects.filter(seat_number__iexact=seat_number).first()
			if not student_match:
				context = self.get_context_data(
					form=form,
					searched=True,
					lookup_error='Seat number not found. Enter the exact seat number from UniPune hall ticket (example: S01423). If it still fails, contact college admin.',
				)
				return self.render_to_response(context)

			lookup_warning = None
			if date_of_birth:
				if student_match.date_of_birth and student_match.date_of_birth != date_of_birth:
					context = self.get_context_data(
						form=form,
						searched=True,
						lookup_error='DOB verification failed. Please enter the correct date of birth.',
					)
					return self.render_to_response(context)
				if not student_match.date_of_birth:
					# If DOB is missing in profile, persist the provided DOB for future verification.
					student_match.date_of_birth = date_of_birth
					student_match.save(update_fields=['date_of_birth'])

			exam_form_submission = ExamFormSubmission.objects.filter(student=student_match).order_by('-submitted_at').first()
			exam_schedules = self._exam_schedules_for_student(student_match, exam_form_submission)
			context = self.get_context_data(
				form=form,
				searched=True,
				student_match=student_match,
				exam_schedules=exam_schedules,
				exam_form_submission=exam_form_submission,
				lookup_warning=lookup_warning,
			)
			return self.render_to_response(context)

		context = self.get_context_data(form=form, searched=True)
		return self.render_to_response(context)


class ProfileView(LoginRequiredMixin, TemplateView):
	"""Basic authenticated user profile page."""
	template_name = 'Students/profile.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['total_students'] = Student.objects.count()
		context['active_students'] = Student.objects.filter(is_active=True).count()
		return context


class RegisterView(CreateView):
	"""User registration view using CustomUserCreationForm."""
	form_class = CustomUserCreationForm
	template_name = 'Students/register.html'
	success_url = reverse_lazy('students:login')

	def form_valid(self, form):
		response = super().form_valid(form)
		messages.success(self.request, 'Registration successful! Please log in.')
		return response


# Admin-only dashboard and CSV export
def staff_check(user):
	return user.is_active and user.is_staff


@method_decorator(user_passes_test(staff_check), name='dispatch')
class AdminDashboardView(TemplateView):
	template_name = 'Students/admin_dashboard.html'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['total_students'] = Student.objects.count()
		context['active_students'] = Student.objects.filter(is_active=True).count()
		context['recent_students'] = Student.objects.order_by('-enrollment_date')[:8]
		# Data for a simple GPA distribution chart
		gpa_counts = Student.objects.values_list('gpa', flat=True)
		gpa_buckets = {}
		for g in gpa_counts:
			if g is None:
				continue
			key = f"{float(g):.1f}"
			gpa_buckets[key] = gpa_buckets.get(key, 0) + 1
		# Prepare labels and values
		labels = sorted(gpa_buckets.keys(), key=float)
		values = [gpa_buckets[k] for k in labels]
		context['chart_labels'] = labels
		context['chart_values'] = values
		return context


@user_passes_test(staff_check)
def export_students_csv(request):
	"""Export all students as CSV (admin only)."""
	response = HttpResponse(content_type='text/csv')
	response['Content-Disposition'] = 'attachment; filename="students_export.csv"'

	writer = csv.writer(response)
	writer.writerow(['id', 'first_name', 'last_name', 'email', 'course', 'gpa', 'is_active', 'enrollment_date'])
	for s in Student.objects.all().order_by('id'):
		writer.writerow([s.id, s.first_name, s.last_name, s.email, s.course, s.gpa, s.is_active, s.enrollment_date])

	return response
