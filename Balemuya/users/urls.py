from django.urls import path
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from rest_framework import generics
from rest_framework.response import Response
from django.http import JsonResponse
from .views import ProfessionalRegisterView
# from .serializers import GoogleLoginSerializer  
class GoogleAuthView(generics.GenericAPIView):
    pass
    # serializer_class = GoogleLoginSerializer
    # adapter_class = GoogleOAuth2Adapter

    # def post(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
        
    #     # Implement your Google login logic here
    #     # For example, you might call some method to handle the login
    #     # return Response({"message": "Google login successful!"})

    #     return Response({"message": "Login logic not implemented."})

def google_callback(request):
    print('Full Path:', request.get_full_path())
    print('GET Parameters:', request.GET)
    
    # Check for the authorization code
    code = request.GET.get('code')
    if code:
        print('Authorization Code:', code)
        # Proceed with token exchange
    else:
        print('Error: No authorization code provided!')
        return JsonResponse({'error': 'No authorization code provided!'}, status=400)

# In your urls.py
urlpatterns = [
 path('auth/register/professional/', ProfessionalRegisterView.as_view(), name='auth-register-professional'),
 path('google-auth/', google_callback, name='google_auth'),

]

