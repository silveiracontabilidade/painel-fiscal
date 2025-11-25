from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


class PainelLoginView(LoginView):
    """Simple login screen to validate credentials before React frontend is ready."""
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True
    success_url = reverse_lazy('welcome')


@login_required
def welcome_view(request: HttpRequest) -> HttpResponse:
    return render(request, 'accounts/welcome.html')


def logout_view(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        from django.contrib.auth import logout

        logout(request)
        return redirect('login')
    return redirect('welcome')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_status(request):
    """JWT-protected endpoint for quick integration tests."""
    return Response(
        {'user': request.user.username, 'message': 'API pronta para o frontend React.'}
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    """Returns authenticated user basic profile data for the React frontend."""
    user = request.user
    return Response(
        {
            'id': user.id,
            'username': user.get_username(),
            'nome': user.get_full_name() or user.get_username(),
            'email': user.email or '',
        }
    )
