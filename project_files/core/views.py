from pyexpat.errors import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Student, Parent, Notes, Quiz, Question
from .forms import NotesForm
from PyPDF2 import PdfReader
import random
import random
import re as regex   
from PyPDF2 import PdfReader
from django.contrib.auth.models import User
from django.contrib import messages as dj_messages
from .models import Parent, Student

# ---------- HOME ----------
def home(request):
    return render(request, "home.html")


# ---------- AUTH ----------
def student_signup(request):
    if request.method == "POST":
        user = User.objects.create_user(
            username=request.POST["email"],
            first_name=request.POST["name"],
            email=request.POST["email"],
            password=request.POST["password"],
        )
        Student.objects.create(
            user=user,
            class_semester=request.POST["class_semester"]
        )
        return redirect("login")
    return render(request, "signup_student.html")




def parent_signup(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        student_email = request.POST.get("student_email")

        # Check if parent email already exists
        if User.objects.filter(username=email).exists():
            dj_messages.error(request, "Email already registered. Please login.")
            return redirect("login")

        # Check if student exists
        try:
            student = Student.objects.get(user__email=student_email)
        except Student.DoesNotExist:
            dj_messages.error(request, "Student email not found.")
            return redirect("parent_signup")

        # Create parent user
        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=name,
            password=password
        )

        # Link parent with student
        Parent.objects.create(user=user, student=student)

        dj_messages.success(request, "Parent account created successfully.")
        return redirect("login")

    return render(request, "signup_parent.html")


def user_login(request):
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST["email"],
            password=request.POST["password"],
        )
        if user:
            login(request, user)
            if hasattr(user, "student"):
                return redirect("student_dashboard")
            return redirect("parent_dashboard")
    return render(request, "login.html")


def user_logout(request):
    logout(request)
    return redirect("home")


# ---------- DASHBOARD ----------
def student_dashboard(request):
    return render(request, "student_dashboard.html")


def parent_dashboard(request):
    return render(request, "parent_dashboard.html")


# ---------- NOTES ----------
def student_notes(request):
    notes = Notes.objects.filter(student=request.user.student)

    if request.method == "POST":
        form = NotesForm(request.POST, request.FILES)
        if form.is_valid():
            note = form.save(commit=False)
            note.student = request.user.student
            note.save()
            return redirect("student_notes")
    else:
        form = NotesForm()

    return render(request, "student_notes.html", {
        "notes": notes,
        "form": form
    })


def delete_note(request, note_id):
    get_object_or_404(Notes, id=note_id).delete()
    return redirect("student_notes")


# ---------- QUIZ HOME ----------
def quiz_home(request):
    student = request.user.student
    notes = Notes.objects.filter(student=student)
    quizzes = Quiz.objects.filter(student=student).order_by("-date")

    return render(request, "quiz_home.html", {
        "notes": notes,
        "quizzes": quizzes
    })


# ---------- GENERATE QUIZ ----------


def generate_quiz(request, note_id):
    note = get_object_or_404(Notes, id=note_id)

    quiz = Quiz.objects.create(
        student=request.user.student,
        subject=note.subject
    )

    
    reader = PdfReader(note.file.path)
    content = ""

    for page in reader.pages:
        text = page.extract_text()
        if text:
            content += text + " "

    
    sentences = regex.split(r'[.\n]', content)
    sentences = [s.strip() for s in sentences if len(s.split()) > 6]

   
    keywords = set()
    for s in sentences:
        for w in s.split():
            if len(w) > 4 and w.isalpha():
                keywords.add(w)

    keywords = list(keywords)

    # 4️⃣ Generate questions
    question_count = 0

    for sentence in sentences:
        words = sentence.split()

        candidates = [w for w in words if len(w) > 4 and w.isalpha()]
        if not candidates:
            continue

        correct = random.choice(candidates)

        question_text = sentence.replace(correct, "_____")

        options = set(random.sample(keywords, min(6, len(keywords))))
        options.add(correct)

        if len(options) < 4:
            continue

        options = random.sample(list(options), 4)

        Question.objects.create(
            quiz=quiz,
            question_text=question_text,
            option_a=options[0],
            option_b=options[1],
            option_c=options[2],
            option_d=options[3],
            correct_answer=correct
        )

        question_count += 1
        if question_count == 20:
            break

    return redirect("take_quiz", quiz_id=quiz.id)


# ---------- TAKE QUIZ ----------
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)
    return render(request, "take_quiz.html", {
        "quiz": quiz,
        "questions": questions
    })


# ---------- SUBMIT QUIZ ----------
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(
        Quiz,
        id=quiz_id,
        student=request.user.student
    )
    questions = Question.objects.filter(quiz=quiz)

    score = 0
    correct_count = 0
    wrong_count = 0
    total = questions.count()

    for q in questions:
        user_answer = request.POST.get(str(q.id))
        q.user_answer = user_answer

        if (
            user_answer
            and q.correct_answer
            and user_answer.strip().lower()
            == q.correct_answer.strip().lower()
        ):
            score += 1
            correct_count += 1
        else:
            wrong_count += 1

    quiz.score = round((score / total) * 100, 2) if total else 0
    quiz.save()

    history_scores = list(
        Quiz.objects.filter(student=request.user.student)
        .order_by("date")
        .values_list("score", flat=True)
    )

    return render(request, "quiz_result.html", {
        "quiz": quiz,
        "questions": questions,
        "correct_count": correct_count,
        "wrong_count": wrong_count,
        "total": total,
        "history_scores": history_scores
    })
def student_progress(request):
    if not hasattr(request.user, "student"):
        return redirect("login")

    quizzes = Quiz.objects.filter(
        student=request.user.student
    ).order_by("date")

    total_quizzes = quizzes.count()

    scores = [q.score for q in quizzes if q.score is not None]

    average_score = round(sum(scores) / len(scores), 2) if scores else 0
    best_score = max(scores) if scores else 0
    worst_score = min(scores) if scores else 0

    return render(
        request,
        "student_progress.html",
        {
            "total_quizzes": total_quizzes,
            "average_score": average_score,
            "best_score": best_score,
            "worst_score": worst_score,
            "scores": scores,
        },
    )
from django.db.models import Avg

def parent_dashboard(request):
    if not hasattr(request.user, "parent"):
        return redirect("login")

    if not request.user.parent.student:
        messages.error(request, "No student linked to this parent.")
        return redirect("login")

    student = request.user.parent.student
    quizzes = Quiz.objects.filter(student=student).order_by("date")
    scores = list(quizzes.values_list("score", flat=True))

    total_quizzes = quizzes.count()
    average_score = round(sum(scores) / total_quizzes, 2) if total_quizzes else 0
    best_score = max(scores) if scores else 0
    worst_score = min(scores) if scores else 0

    return render(request, "parent_dashboard.html", {
        "student": student,
        "quizzes": quizzes,
        "scores": scores,
        "total_quizzes": total_quizzes,
        "average_score": average_score,
        "best_score": best_score,
        "worst_score": worst_score,
    })
