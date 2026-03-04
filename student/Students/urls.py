from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from .forms import CustomAuthenticationForm, CustomPasswordResetForm, CustomSetPasswordForm
from . import views as students_views
from . import views

app_name = 'students'

urlpatterns = [
    path('college/', views.CollegeWebsiteHomeView.as_view()),
    path('college/courses/', views.CollegeCoursesView.as_view(), name='college_courses'),
    path('college/admissions/', views.CollegeAdmissionsView.as_view(), name='college_admissions'),
    path('college/exam-form/', views.CollegeExamStudentLoginView.as_view(), name='college_exam_form'),
    path('college/exam-form/student-dashboard/', views.CollegeExamStudentDashboardView.as_view(), name='college_exam_student_dashboard'),
    path('college/exam-form/portal/', views.CollegeExamPortalView.as_view(), name='college_exam_portal'),
    path('college/exam-form/dashboard/', views.CollegeExamDashboardView.as_view(), name='college_exam_dashboard'),
    path('college/exam-form/fill/', views.CollegeExamFormView.as_view(), name='college_exam_form_fill'),
    path('college/hall-ticket/', views.CollegeHallTicketView.as_view(), name='college_hall_ticket'),
    path('college/results/', views.CollegeOnlineResultView.as_view(), name='college_results'),
    path('college/departments/', views.CollegeDepartmentsView.as_view(), name='college_departments'),
    path('college/faculty/', views.CollegeFacultyView.as_view(), name='college_faculty'),
    path('college/contact/', views.CollegeContactView.as_view(), name='college_contact'),
    path('', views.CollegeWebsiteHomeView.as_view(), name='home'),
    path('home/', views.CollegeWebsiteHomeView.as_view()),
    path('about/', views.AboutPageView.as_view(), name='about'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('workflows/', views.WorkflowHubView.as_view(), name='workflow_hub'),
    path('workflows/complete-flow/', views.WorkflowCompleteFlowView.as_view(), name='workflow_complete_flow'),
    path('admin-panel/', views.AdminDashboardView.as_view(), name='admin_panel'),
    path('students/', views.StudentListView.as_view(), name='list'),
    path('add/', views.StudentCreateView.as_view(), name='add'),
    path('<int:pk>/', views.StudentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.StudentUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.StudentDeleteView.as_view(), name='delete'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('admin/export-csv/', views.export_students_csv, name='export_csv'),
    path('workflows/admissions/', views.AdmissionApplicationListView.as_view(), name='admission_list'),
    path('workflows/admissions/new/', views.AdmissionApplicationCreateView.as_view(), name='admission_add'),
    path('workflows/attendance/', views.AttendanceRecordListView.as_view(), name='attendance_list'),
    path('workflows/attendance/new/', views.AttendanceRecordCreateView.as_view(), name='attendance_add'),
    path('workflows/exams/schedules/', views.ExamScheduleListView.as_view(), name='exam_schedule_list'),
    path('workflows/exams/schedules/new/', views.ExamScheduleCreateView.as_view(), name='exam_schedule_add'),
    path('workflows/exams/results/', views.ExamResultListView.as_view(), name='exam_result_list'),
    path('workflows/exams/results/new/', views.ExamResultCreateView.as_view(), name='exam_result_add'),
    path('workflows/fees/structures/', views.FeeStructureListView.as_view(), name='fee_structure_list'),
    path('workflows/fees/structures/new/', views.FeeStructureCreateView.as_view(), name='fee_structure_add'),
    path('workflows/fees/invoices/', views.FeeInvoiceListView.as_view(), name='fee_invoice_list'),
    path('workflows/fees/invoices/new/', views.FeeInvoiceCreateView.as_view(), name='fee_invoice_add'),
    path('workflows/fees/payments/', views.FeePaymentListView.as_view(), name='fee_payment_list'),
    path('workflows/fees/payments/new/', views.FeePaymentCreateView.as_view(), name='fee_payment_add'),
    path('workflows/rooms/', views.RoomListView.as_view(), name='room_list'),
    path('workflows/rooms/new/', views.RoomCreateView.as_view(), name='room_add'),
    path('workflows/timetable/', views.TimetableEntryListView.as_view(), name='timetable_list'),
    path('workflows/timetable/new/', views.TimetableEntryCreateView.as_view(), name='timetable_add'),
    path('login/', students_views.CustomLoginView.as_view(template_name='Students/login.html', authentication_form=CustomAuthenticationForm), name='login'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='Students/password_reset_form.html',
        form_class=CustomPasswordResetForm,
        email_template_name='Students/password_reset_email.txt',
        subject_template_name='Students/password_reset_subject.txt',
        success_url=reverse_lazy('students:password_reset_done')
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='Students/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='Students/password_reset_confirm.html',
        form_class=CustomSetPasswordForm,
        success_url=reverse_lazy('students:password_reset_complete')
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='Students/password_reset_complete.html'
    ), name='password_reset_complete'),
    path('logout/', students_views.logout_view, name='logout'),
]
