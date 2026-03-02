from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
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
from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import re


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
			display_structures.append({
				'structure': structure,
				'admission_fee': admission_fee,
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
			mother_name = form.cleaned_data['mother_name']
			father_name = form.cleaned_data['father_name']
			seat_student = Student.objects.filter(seat_number__iexact=seat_number).first()
			if not seat_student:
				context = self.get_context_data(
					form=form,
					searched=True,
					selected_course=selected_course,
					lookup_error='Seat number not found. Please check the seat number.',
				)
				return self.render_to_response(context)

			has_parent_data = any([
				(seat_student.mother_name or '').strip(),
				(seat_student.father_name or '').strip(),
				(seat_student.parent_name or '').strip(),
			])
			if not has_parent_data:
				context = self.get_context_data(
					form=form,
					searched=True,
					selected_course=selected_course,
					lookup_error='Student profile is incomplete: mother/father name is not saved by admin.',
				)
				return self.render_to_response(context)

			student_match = Student.objects.filter(
				pk=seat_student.pk
			).filter(
				Q(mother_name__iexact=mother_name) | Q(parent_name__iexact=mother_name),
				Q(father_name__iexact=father_name) | Q(parent_name__iexact=father_name),
			).first()
			if not student_match:
				context = self.get_context_data(
					form=form,
					searched=True,
					selected_course=selected_course,
					lookup_error='Seat found, but mother/father name does not match our records.',
				)
				return self.render_to_response(context)

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
			)
			return self.render_to_response(context)

		context = self.get_context_data(form=form, searched=True, selected_course=selected_course)
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
