from django.contrib import admin
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


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
	list_display = ('id', 'seat_number', 'first_name', 'last_name', 'date_of_birth', 'email', 'course', 'gpa', 'is_active', 'enrollment_date')
	list_display_links = ('id', 'first_name')
	search_fields = ('seat_number', 'first_name', 'last_name', 'email', 'course')
	list_filter = ('is_active', 'course')
	ordering = ('-enrollment_date', 'last_name')


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
	list_display = ('id', 'student', 'program', 'session', 'application_date', 'status', 'merit_score')
	search_fields = ('student__first_name', 'student__last_name', 'program', 'session')
	list_filter = ('status', 'session')
	ordering = ('-application_date',)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
	list_display = ('id', 'student', 'attendance_date', 'status', 'remarks')
	search_fields = ('student__first_name', 'student__last_name', 'remarks')
	list_filter = ('status', 'attendance_date')
	ordering = ('-attendance_date',)


@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
	list_display = ('id', 'title', 'course', 'subject', 'exam_type', 'exam_date', 'start_time', 'end_time')
	search_fields = ('title', 'course', 'subject')
	list_filter = ('exam_type', 'exam_date', 'course')
	ordering = ('-exam_date', 'start_time')


@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
	list_display = ('id', 'student', 'exam', 'marks_obtained', 'grade')
	search_fields = ('student__first_name', 'student__last_name', 'exam__title', 'exam__subject')
	list_filter = ('exam__exam_date', 'exam__course')
	ordering = ('-exam__exam_date',)


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'course', 'academic_year', 'total_amount', 'is_active')
	search_fields = ('name', 'course', 'academic_year')
	list_filter = ('course', 'academic_year', 'is_active')
	ordering = ('-academic_year', 'course')


@admin.register(FeeInvoice)
class FeeInvoiceAdmin(admin.ModelAdmin):
	list_display = ('id', 'invoice_number', 'student', 'total_amount', 'status', 'issue_date', 'due_date')
	search_fields = ('invoice_number', 'student__first_name', 'student__last_name')
	list_filter = ('status', 'issue_date', 'due_date')
	ordering = ('-issue_date',)


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
	list_display = ('id', 'invoice', 'payment_date', 'amount', 'method', 'transaction_reference')
	search_fields = ('invoice__invoice_number', 'transaction_reference')
	list_filter = ('method', 'payment_date')
	ordering = ('-payment_date',)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'capacity', 'is_lab')
	search_fields = ('name',)
	list_filter = ('is_lab',)
	ordering = ('name',)


@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
	list_display = ('id', 'course', 'section', 'subject', 'faculty_name', 'weekday', 'start_time', 'end_time', 'room')
	search_fields = ('course', 'section', 'subject', 'faculty_name', 'room__name')
	list_filter = ('weekday', 'course', 'section')
	ordering = ('weekday', 'start_time')
