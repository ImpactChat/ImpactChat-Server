from json import loads

import django
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.decorators import method_decorator
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import View

from django_react_views.views import ReactTemplateView

from .models import Student, User

# pylint: disable=no-member
student_type = ContentType.objects.get(app_label="impactadmin", model="student")
teacher_type = ContentType.objects.get(app_label="impactadmin", model="teacher")
staff_type = ContentType.objects.get(app_label="impactadmin", model="staff")
parent_type = ContentType.objects.get(app_label="impactadmin", model="parent")
class_type = ContentType.objects.get(app_label="impactadmin", model="class")

types = {
    "student": student_type,
    "teacher": teacher_type,
    "staff": staff_type,
    "parent": parent_type,
    "class": class_type,
}


def can_administer(request):
    teacher_type = ContentType.objects.get(app_label="impactadmin", model="teacher")
    staff_type = ContentType.objects.get(app_label="impactadmin", model="staff")
    return (
        request.user.user_role == teacher_type or request.user.user_role == staff_type
    )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(ReactTemplateView, UserPassesTestMixin):
    """
    Present the user with a login screen and authenticate him
    """

    react_component = "login.jsx"
    template_name = "impactadmin/login.html"

    # redirect to dashboard if user is already authed
    @method_decorator(
        user_passes_test(
            lambda u: not u.is_authenticated,
            login_url=reverse_lazy("impactadmin:dashboard"),
            redirect_field_name=None,
        )
    )
    def dispatch(self, *args, **kwargs):
        return super(LoginView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = authenticate(
            username=request.POST.get("username"), password=request.POST.get("password")
        )
        if user is not None:
            login(request, user)
            redirect_url = request.GET.get("next", None)
            if redirect_url is not None:
                return redirect(redirect_url)
            return redirect("impactadmin:dashboard")
        else:
            messages.warning(request, "Incorrect username or password")
            return redirect("impactadmin:login")


class LogoutView(View):
    """
    Logs out the logged in users if any and redirects to the login page
    """

    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect("impactadmin:login")


class DashboardView(LoginRequiredMixin, ReactTemplateView):
    """
    Present the logged in user with their dashboard, and redirect to the login
    page if they're not logged in
    """

    template_name = "impactadmin/dashboard.html"
    react_component = "dashboard.jsx"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ProfileView(LoginRequiredMixin, ReactTemplateView):
    """
    Present the logged in user with their dashboard, and redirect to the login
    page if they're not logged in
    """

    template_name = "impactadmin/dashboard.html"
    react_component = "profile.jsx"

    def post(self, request):
        data = loads(request.body.decode("UTF-8"))
        try:
            request.user.locale = data["language"]
            request.user.save()
        except Exception as e:
            raise e
        # request.user.locale
        return JsonResponse(data)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        translation.activate(self.request.user.locale)
        context["props"] = {
            "curlang": translation.get_language(),
            "availableLang": settings.LANGUAGES,
        }
        return context


@method_decorator(ensure_csrf_cookie, name="dispatch")
class AdministrationView(LoginRequiredMixin, UserPassesTestMixin, ReactTemplateView):
    """
    Display the administration interface to the user given they are in the
    a group with the correct permissions to access it
    """

    template_name = "impactadmin/administration.html"
    react_component = "administration.jsx"

    def post(self, request):
        data = loads(request.body.decode("UTF-8"))
        try:
            request.user.locale = data["language"]
            request.user.save()
        except Exception as e:
            raise e
        # request.user.locale
        return JsonResponse(data)

    def test_func(self):
        return can_administer(self.request)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data()
        translation.activate(self.request.user.locale)
        context["props"] = {
            "models": [
                {
                    "name": _("students"),
                    "api-name": "student",
                    "count": User.objects.filter(user_role=student_type).count(),
                    "api-link:get": reverse_lazy("impactadmin-api:get"),
                },
                {
                    "name": _("teachers"),
                    "api-name": "teacher",
                    "count": User.objects.filter(user_role=teacher_type).count(),
                    "api-link:get": reverse_lazy("impactadmin-api:get"),
                },
                {
                    "name": _("classes"),
                    "api-name": "class",
                    "count": User.objects.filter(user_role=class_type).count(),
                    "api-link:get": reverse_lazy("impactadmin-api:get"),
                },
                {
                    "name": _("parents"),
                    "api-name": "parent",
                    "count": User.objects.filter(user_role=parent_type).count(),
                    "api-link:get": reverse_lazy("impactadmin-api:get"),
                },
                {
                    "name": _("staff"),
                    "api-name": "staff",
                    "count": User.objects.filter(user_role=staff_type).count(),
                    "api-link:get": reverse_lazy("impactadmin-api:get"),
                },
            ]
        }
        return context


class AdministrationAPIView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Return students as a JSON response, supports pagination
    """

    template_name = "impactadmin/administration.html"
    react_component = "administration.jsx"

    def get(self, request):
        qs = User.objects.filter(user_role=types[request.GET.get("type")])
        p = Paginator(qs, request.GET.get("max", 10))
        student_data = []
        count = qs.count()
        try:
            page = p.page(request.GET.get("page", 1))
            for student in page.object_list:
                student_data.append(student.getJSON())
                student_data[-1]["full name"] = student.get_full_name()
                student_data[-1]["pk"] = student.pk
        except django.core.paginator.EmptyPage:
            student_data = [None]

        data = {
            "items": student_data,
            "count": count,
            "min_page": 1,
            "max_page": p.num_pages,
        }

        return JsonResponse(data)

    def test_func(self):
        return can_administer(self.request)
