from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages as dj_messages

from .models import Student, Parent, Notes, Quiz, Question
from .forms import NotesForm

from PyPDF2 import PdfReader

import random
import re as regex


# ---------- HOME ----------
def home(request):

    return render(request, "home.html")


# ---------- STUDENT SIGNUP ----------
def student_signup(request):

    if request.method == "POST":

        try:

            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            class_semester = request.POST.get("class_semester")

            if not name or not email or not password or not class_semester:

                return render(request, "signup_student.html", {
                    "error": "All fields are required"
                })

            if User.objects.filter(username=email).exists():

                return render(request, "signup_student.html", {
                    "error": "Email already exists"
                })

            user = User.objects.create_user(
                username=email,
                first_name=name,
                email=email,
                password=password
            )

            Student.objects.create(
                user=user,
                class_semester=class_semester
            )

            login(request, user)

            return redirect("student_dashboard")

        except Exception as e:

            return render(request, "signup_student.html", {
                "error": str(e)
            })

    return render(request, "signup_student.html")


# ---------- PARENT SIGNUP ----------
def parent_signup(request):

    if request.method == "POST":

        try:

            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            student_email = request.POST.get("student_email")

            if User.objects.filter(username=email).exists():

                dj_messages.error(
                    request,
                    "Email already registered"
                )

                return redirect("parent_signup")

            try:

                student = Student.objects.get(
                    user__email=student_email
                )

            except Student.DoesNotExist:

                dj_messages.error(
                    request,
                    "Student email not found"
                )

                return redirect("parent_signup")

            user = User.objects.create_user(
                username=email,
                email=email,
                first_name=name,
                password=password
            )

            Parent.objects.create(
                user=user,
                student=student
            )

            dj_messages.success(
                request,
                "Parent account created successfully"
            )

            return redirect("login")

        except Exception as e:

            dj_messages.error(
                request,
                str(e)
            )

            return redirect("parent_signup")

    return render(request, "signup_parent.html")


# ---------- LOGIN ----------
def user_login(request):

    if request.method == "POST":

        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=email,
            password=password
        )

        if user is not None:

            login(request, user)

            if hasattr(user, "student"):
                return redirect("student_dashboard")

            elif hasattr(user, "parent"):
                return redirect("parent_dashboard")

            else:
                return redirect("home")

        else:

            dj_messages.error(
                request,
                "Invalid email or password"
            )

    return render(request, "login.html")


# ---------- LOGOUT ----------
def user_logout(request):

    logout(request)

    return redirect("home")


# ---------- STUDENT DASHBOARD ----------
@login_required
def student_dashboard(request):

    if not hasattr(request.user, "student"):

        return redirect("login")

    student = request.user.student

    total_notes = Notes.objects.filter(
        student=student
    ).count()

    quizzes = Quiz.objects.filter(
        student=student
    )

    total_quizzes = quizzes.count()

    scores = [
        q.score
        for q in quizzes
        if q.score is not None
    ]

    avg_score = (
        round(sum(scores) / len(scores), 2)
        if scores else 0
    )

    last_quiz = quizzes.order_by("-date").first()

    last_score = (
        last_quiz.score
        if last_quiz else 0
    )

    return render(request, "student_dashboard.html", {
        "student": student,
        "total_notes": total_notes,
        "total_quizzes": total_quizzes,
        "avg_score": avg_score,
        "last_score": last_score,
    })


# ---------- STUDENT NOTES ----------
@login_required
def student_notes(request):

    if not hasattr(request.user, "student"):

        return redirect("login")

    notes = Notes.objects.filter(
        student=request.user.student
    )

    if request.method == "POST":

        form = NotesForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            note = form.save(commit=False)

            note.student = request.user.student

            note.save()

            dj_messages.success(
                request,
                "Note uploaded successfully"
            )

            return redirect("student_notes")

    else:

        form = NotesForm()

    return render(request, "student_notes.html", {
        "notes": notes,
        "form": form
    })


# ---------- DELETE NOTE ----------
@login_required
def delete_note(request, note_id):

    note = get_object_or_404(
        Notes,
        id=note_id
    )

    if note.student == request.user.student:

        if note.file:
            note.file.delete()

        note.delete()

        dj_messages.success(
            request,
            "Note deleted successfully"
        )

    return redirect("student_notes")


# ---------- QUIZ HOME ----------
@login_required
def quiz_home(request):

    student = request.user.student

    notes = Notes.objects.filter(
        student=student
    )

    quizzes = Quiz.objects.filter(
        student=student
    ).order_by("-date")

    return render(request, "quiz_home.html", {
        "notes": notes,
        "quizzes": quizzes
    })


# ---------- GENERATE QUIZ ----------
@login_required
def generate_quiz(request, note_id):

    try:

        note = get_object_or_404(
            Notes,
            id=note_id
        )

        reader = PdfReader(note.file.path)

        content = ""

        for page in reader.pages:

            text = page.extract_text()

            if text:
                content += text + " "

        content = content.strip()

        print("PDF CONTENT:", content)

        # Check PDF text
        if len(content) < 50:

            dj_messages.error(
                request,
                "PDF has very little readable text."
            )

            return redirect("quiz_home")

        sentences = regex.split(r'[.\n]', content)

        sentences = [

            s.strip()

            for s in sentences

            if len(s.split()) > 5

        ]

        print("SENTENCES:", sentences)

        if not sentences:

            dj_messages.error(
                request,
                "No valid sentences found."
            )

            return redirect("quiz_home")

        quiz = Quiz.objects.create(

            student=request.user.student,

            subject=note.subject

        )

        question_count = 0

        for sentence in sentences[:10]:

            words = [

                w for w in sentence.split()

                if len(w) > 4 and w.isalpha()

            ]

            if len(words) < 4:
                continue

            correct = random.choice(words)

            question_text = sentence.replace(
                correct,
                "_____"
            )

            wrong_options = random.sample(words, 3)

            options = wrong_options + [correct]

            random.shuffle(options)

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

        print("QUESTIONS CREATED:", question_count)

        if question_count == 0:

            quiz.delete()

            dj_messages.error(
                request,
                "Quiz generation failed."
            )

            return redirect("quiz_home")

        return redirect(
            "take_quiz",
            quiz_id=quiz.id
        )

    except Exception as e:

        print("QUIZ ERROR:", e)

        dj_messages.error(
            request,
            f"Error: {str(e)}"
        )

        return redirect("quiz_home")
# ---------- TAKE QUIZ ----------
@login_required
def take_quiz(request, quiz_id):

    quiz = get_object_or_404(
        Quiz,
        id=quiz_id
    )

    questions = Question.objects.filter(
        quiz=quiz
    )

    return render(request, "take_quiz.html", {
        "quiz": quiz,
        "questions": questions
    })


# ---------- SUBMIT QUIZ ----------
@login_required
def submit_quiz(request, quiz_id):

    quiz = get_object_or_404(
        Quiz,
        id=quiz_id,
        student=request.user.student
    )

    questions = Question.objects.filter(
        quiz=quiz
    )

    score = 0

    correct_count = 0

    wrong_count = 0

    total = questions.count()

    for q in questions:

        user_answer = request.POST.get(str(q.id))

        if (
            user_answer
            and user_answer.strip().lower()
            == q.correct_answer.strip().lower()
        ):

            score += 1

            correct_count += 1

        else:

            wrong_count += 1

    quiz.score = (
        round((score / total) * 100, 2)
        if total else 0
    )

    quiz.save()

    history_scores = list(

        Quiz.objects.filter(
            student=request.user.student
        ).order_by("date")
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


# ---------- STUDENT PROGRESS ----------
@login_required
def student_progress(request):

    quizzes = Quiz.objects.filter(
        student=request.user.student
    ).order_by("date")

    total_quizzes = quizzes.count()

    scores = [
        q.score
        for q in quizzes
        if q.score is not None
    ]

    average_score = (
        round(sum(scores) / len(scores), 2)
        if scores else 0
    )

    best_score = max(scores) if scores else 0

    worst_score = min(scores) if scores else 0

    return render(request, "student_progress.html", {
        "quizzes": quizzes,
        "total_quizzes": total_quizzes,
        "average_score": average_score,
        "best_score": best_score,
        "worst_score": worst_score,
    })


# ---------- PARENT DASHBOARD ----------
@login_required
def parent_dashboard(request):

    if not hasattr(request.user, "parent"):

        return redirect("login")

    student = request.user.parent.student

    quizzes = Quiz.objects.filter(
        student=student
    ).order_by("date")

    scores = list(
        quizzes.values_list("score", flat=True)
    )

    total_quizzes = quizzes.count()

    average_score = (
        round(sum(scores) / total_quizzes, 2)
        if total_quizzes else 0
    )

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