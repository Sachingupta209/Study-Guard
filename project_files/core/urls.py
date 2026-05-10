from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('signup/student/', views.student_signup, name='student_signup'),
    path('signup/parent/', views.parent_signup, name='parent_signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('parent/dashboard/', views.parent_dashboard, name='parent_dashboard'),

    path('student/notes/', views.student_notes, name='student_notes'),
    path('student/notes/delete/<int:note_id>/', views.delete_note, name='delete_note'),

    path('student/quiz/', views.quiz_home, name='quiz_home'),
    path('student/quiz/generate/<int:note_id>/', views.generate_quiz, name='generate_quiz'),
    path('student/quiz/take/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('student/quiz/submit/<int:quiz_id>/', views.submit_quiz, name='submit_quiz'),
    path("student/progress/", views.student_progress, name="student_progress"),
    path("parent/dashboard/", views.parent_dashboard, name="parent_dashboard"),

]
