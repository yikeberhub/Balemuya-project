import requests
import uuid
import json
from django.core.cache import cache
from django.contrib.auth import login
from django.db import transaction
from django.utils import timezone

from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken

from django.conf import settings

from allauth.account.models import get_adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.models import SocialApp

# from fcm_django.models import FCMDevice

from urllib.parse import parse_qs

from .models import User, Professional, Customer, Admin,Payment,SubscriptionPlan,Payment,Skill,Education,Portfolio,Certificate,Address,VerificationRequest
from common.models import Category
from .utils import send_sms, generate_otp, send_email_confirmation,notify_user

from .serializers import  LoginSerializer ,ProfessionalSerializer, CustomerSerializer, AdminSerializer,\
    VerificationRequestSerializer,PortfolioSerializer,CertificateSerializer,EducationSerializer,SkillSerializer,PaymentSerializer,SubscriptionPlanSerializer
    
from common.serializers import UserSerializer, AddressSerializer,CategorySerializer
class RegisterFCMDeviceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        device_type = request.data.get("type")  # e.g., "web", "android", or "ios"

        if token:
            device, created = FCMDevice.objects.update_or_create(
                user=request.user, 
                registration_id=token,
                defaults={"type": device_type}
            )
            return Response({"message": "Device registered successfully."})
        return Response({"error": "Token is required."}, status=400)


class RegisterView(APIView):
    serializer_class = UserSerializer
    
    def post(self, request, *args, **kwargs):
        serializer_class = self.serializer_class
        serializer = serializer_class(data=request.data)
        if serializer.is_valid():
            user_instance = serializer.save()
            token = default_token_generator.make_token(user_instance)
            uid = urlsafe_base64_encode(str(user_instance.pk).encode())
            
            current_domain = request.get_host()
            verification_link = f'http://{current_domain}/api/users/auth/verify-email/?uid={uid}&token={token}'
            
            subject = 'Verify your email for Balemuya.'
            message = f'Please click the link below to verify your email for Balemuya.\n\n{verification_link}'
            recipient_list = [user_instance.email]
            
            # send confirmation email
            print('email send start')
            send_email_confirmation(subject, message, recipient_list)
            print('email send end')
            
            otp = generate_otp()
            cache.set(f"otp_{user_instance.email}", otp, timeout=300)
            
            cached = cache.get(f"otp_{user_instance.email}")
            print('cached otp', cached)
        
            phone_number = user_instance.phone_number
            message_body = f"Hello {user_instance.get_full_name()}, your OTP is {otp}. It is only valid for 5 minutes."
            send_sms(request, to=phone_number, message_body=message_body)
            
            return Response({
                'message': 'Registration successful. Please check your email to verify your account.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmailView(APIView):
    def get(self, request):
        uidb64 = request.GET.get('uid')
        token = request.GET.get('token')
        
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({'message': 'Email verified successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid verification link.'}, status=status.HTTP_400_BAD_REQUEST)

class VerifyPhoneView(APIView):
    
    def post(self, request):
        otp = int(request.data.get('otp'))
        print('otp', otp)
        email = request.data.get('email')
        print('email', email)
        cached_otp = cache.get(f"otp_{email}")
        print('cached otp', cached_otp)
        
        if cached_otp == otp:
            print('otp is valid')
            user = User.objects.filter(email=email).first()
            user.is_active = True
            user.save()
            cache.delete(f"otp_{email}")
            return Response({'message': 'OTP verified successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP, please type again.'}, status=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    permission_classes = (AllowAny,)
    pass

class SetPasswordView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        user = User.objects.filter(email=email).first()
        
        if user:
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password set successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid email.'}, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            otp = generate_otp()
            cache.set(f"otp_{user.email}", otp, timeout=300)
            phone_number = user.phone_number
            message_body = f"Hello {user.get_full_name()}, your OTP is {otp}. It is only valid for 5 minutes."
            send_sms(request, to=phone_number, message_body=message_body)
            return Response({'message': 'OTP sent successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid email.'}, status=status.HTTP_400_BAD_REQUEST)

class VerifyPasswordResetOTPView(APIView):
    
    def post(self, request, *args, **kwargs):
        otp = int(request.data.get('otp'))
        email = request.data.get('email')
        cached_otp = cache.get(f"otp_{email}")
        if cached_otp == otp:
            return Response({'message': 'OTP verified successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP, please type again.'}, status=status.HTTP_400_BAD_REQUEST)

class UpdatePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user = request.user
        print('user', user.password)
        password = user.password
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        if not check_password(old_password, password):
            return Response({'error': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        if old_password == new_password:
            return Response({'error': 'New password should be different from old password.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(id=user.id)
        user.set_password(new_password)
        user.save()
        return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)

class VerifyPasswordResetOTPView(APIView):
    def post(self, request, *args, **kwargs):
        otp = int(request.data.get('otp'))
        email = request.data.get('email')
        cached_otp = cache.get(f"otp_{email}")
        if cached_otp == otp:
            return Response({'message': 'OTP verified successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid OTP, please type again.'}, status=status.HTTP_400_BAD_REQUEST)
        
class GoogleLoginView(APIView):
    def get(self, request):
        code = request.GET.get('code')  
        print('code', code)

        if not code:
            return Response({'error': "Missing code parameter"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            token_url = 'https://oauth2.googleapis.com/token'
            data = {
                'code': code,
                'client_id': settings.GOOGLE_CLIENT_ID,
                'client_secret': settings.GOOGLE_CLIENT_SECRET,
                'redirect_uri': 'http://localhost:3000/auth/google-callback/', 
                'grant_type': 'authorization_code',
            }
            token_response = requests.post(token_url, data=data)
            token_data = token_response.json()

            access_token = token_data.get('access_token')
            if not access_token:
                return Response({'error': "No access token received"}, status=status.HTTP_400_BAD_REQUEST)

            # Get user info from Google
            user_info_response = requests.get(
                'https://people.googleapis.com/v1/people/me?personFields=names,emailAddresses',
                headers={'Authorization': f'Bearer {access_token}'}
            )

            if user_info_response.status_code != 200:
                return Response({'error': user_info_response.json().get('error', 'Unknown error')}, status=status.HTTP_400_BAD_REQUEST)

            user_info = user_info_response.json()
            names = user_info.get('names', [{}])
            email_addresses = user_info.get('emailAddresses', [{}])

            first_name = names[0].get('givenName', '')
            last_name = names[0].get('unstructuredName', '')
            email = email_addresses[0].get('value', '')

            if not email:
                return Response({"error": "Email not found in user info"}, status=status.HTTP_400_BAD_REQUEST)

            # Create or retrieve the user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'password': 'temporarypassword123',
                    'is_active': True
                }
            )

            # Generate access and refresh tokens
            access = AccessToken.for_user(user)
            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(access),
                'refresh': str(refresh),
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        user = User.objects.filter(email=email).first()
        
        if user is None:
            return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.check_password(password):
            return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({'error': 'Your account is not active. Please check your email to verify your account.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user:
            refresh = RefreshToken.for_user(user)
            access = str(refresh.access_token)
            refresh = str(refresh)
            return Response({'message': 'Successfully logged in.',
                             "user": {
                                 'id': user.id,
                                 'email': user.email,
                                 'user_type': user.user_type,
                                 'access': access,
                                 'refresh': refresh,
                             }
                            }, status=status.HTTP_200_OK)
        
        return Response({'error': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            auth_header = request.headers.get('Authorization')

            if not auth_header or not auth_header.startswith('Bearer '):
                return Response({"error": "Authorization header with Bearer token is required."}, status=status.HTTP_400_BAD_REQUEST)

            access_token = auth_header.split(' ')[1]

            user = request.user

            tokens = OutstandingToken.objects.filter(user=user)
            for token in tokens:
                if not BlacklistedToken.objects.filter(token=token).exists():
                    BlacklistedToken.objects.create(token=token)

            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user is None:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        if user.user_type == 'customer': 
            customer = Customer.objects.filter(user=user).first()
            if customer is None:
                return Response({'error': 'Customer not found.'}, status=status.HTTP_404_NOT_FOUND)
            serializer = CustomerSerializer(customer)
            return Response({'user': serializer.data}, status=status.HTTP_200_OK)
        
        if user.user_type == 'professional':
            professional = Professional.objects.filter(user=user).first()
            if professional is None:
                return Response({'error': 'Professional not found.'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ProfessionalSerializer(professional)
            notify_user(user.id,'professional logs in successfully!!!')
            return Response({'user': serializer.data}, status=status.HTTP_200_OK)
        
        if user.user_type == 'admin':
            admin = Admin.objects.filter(user=user).first()
            serializer = AdminSerializer(admin)
            return Response({'user': serializer.data}, status=status.HTTP_200_OK)

        else:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

class UserUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def put(self, request):
        user = request.user
        serializer = self.serializer_class(instance=user, data=request.data, partial=True)
        # Validate and save the profile
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AddressView(APIView):
    permission_class = [IsAuthenticated]
    serializer_class = AddressSerializer
    
    def post(self,request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def put(self,request,pk):
        print('pk is',pk)
        address = Address.objects.get(id=pk,user=request.user)
        serializer = self.serializer_class(address,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_200_OK)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self,request,pk):
        address = Address.objects.get(id=pk,user=request.user)
        address.delete()
        return Response({"message":"Address deleted successfully"},status=status.HTTP_200_OK)
    
        


class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_serializer_class(self):
        user = self.get_object()

        if user.user_type == 'professional':
            return ProfessionalSerializer
        elif user.user_type == 'customer':
            return CustomerSerializer
        elif user.user_type == 'admin':
            return AdminSerializer
        else:
            return None

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        serializer_class = self.get_serializer_class()

        if serializer_class is None:
            return Response({'error': 'User type not recognized'}, status=status.HTTP_400_BAD_REQUEST)

        if user.user_type == 'professional':
            professional_profile = Professional.objects.filter(user=user).first()
            if professional_profile is None:
                return Response({'error': 'Professional profile not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = serializer_class(professional_profile)

        elif user.user_type == 'customer':
            customer_profile = Customer.objects.filter(user=user).first()
            if customer_profile is None:
                return Response({'error': 'Customer profile not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = serializer_class(customer_profile)

        elif user.user_type == 'admin':
            admin_profile = Admin.objects.filter(user=user).first()
            if admin_profile is None:
                return Response({'error': 'Admin profile not found'}, status=status.HTTP_404_NOT_FOUND)
            serializer = serializer_class(admin_profile)

        return Response({
            'message': "Profile fetched successfully",
            'data': serializer.data
        }, status=status.HTTP_200_OK)

class UserDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def delete(self, request, pk, *args, **kwargs):
        user = self.get_object(pk)

        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        user.delete()
        return Response({'message': 'User deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
    
class UserBlockView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist:
            return None

    def put(self, request, pk, *args, **kwargs):
        user = self.get_object(pk)
        print('user is',user)

        if user is None:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if user.is_blocked:
            user.is_blocked=False
            user.save()
            return Response({'message': 'User Unblocked successfully'}, status=status.HTTP_200_OK)
        
        elif not user.is_blocked:
            user.is_blocked=True
            user.save()
            return Response({'message': 'User blocked successfully'}, status=status.HTTP_200_OK)


class ProfessionalProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        professional = request.user.professional
        serializer = ProfessionalSerializer(professional, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# views related to professional
class ProfessionalSkillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            professional = Professional.objects.get(user=request.user)
            skill_names = request.data.get("names", [])  # Accept a list of skill names

            if not skill_names or not isinstance(skill_names, list):
                return Response({"detail": "A list of skill names is required."}, status=status.HTTP_400_BAD_REQUEST)

            added_skills = []
            for name in skill_names:
                skill, created = Skill.objects.get_or_create(name=name)
                professional.skills.add(skill)
                added_skills.append({"id": skill.id, "name": skill.name})

            return Response(
                {"detail": "Skills added successfully.", "skills": added_skills},
                status=status.HTTP_201_CREATED
            )
        except Professional.DoesNotExist:
            return Response({"detail": "Professional not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        """
        Remove a skill from the authenticated professional.
        """
        try:
            professional = Professional.objects.get(user=request.user)
            skill_id = request.data.get("id")

            if not skill_id:
                return Response({"detail": "Skill ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            skill = Skill.objects.get(id=skill_id)
            professional.skills.remove(skill)

            return Response(
                {"detail": "Skill removed successfully.", "skill": {"id": skill.id, "name": skill.name}},
                status=status.HTTP_200_OK
            )
        except Professional.DoesNotExist:
            return Response({"detail": "Professional not found."}, status=status.HTTP_404_NOT_FOUND)
        except Skill.DoesNotExist:
            return Response({"detail": "Skill not found."}, status=status.HTTP_404_NOT_FOUND)

class ProfessionalCategoryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            professional = Professional.objects.get(user=request.user)
            category_names = request.data.get("names", [])  # Accept a list of category names

            if not category_names or not isinstance(category_names, list):
                return Response({"detail": "A list of category names is required."}, status=status.HTTP_400_BAD_REQUEST)

            added_categories = []
            for name in category_names:
                category, created = Category.objects.get_or_create(name=name)
                professional.categories.add(category)
                added_categories.append({"id": category.id, "name": category.name})

            return Response(
                {"detail": "Categories added successfully.", "categories": added_categories},
                status=status.HTTP_201_CREATED
            )
        except Professional.DoesNotExist:
            return Response({"detail": "Professional not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        try:
            professional = Professional.objects.get(user=request.user)
            category_id = request.data.get("id")

            if not category_id:
                return Response({"detail": "Category ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            category = Category.objects.get(id=category_id)
            professional.categories.remove(category)

            return Response(
                {"detail": "Category removed successfully.", "category": {"id": category.id, "name": category.name}},
                status=status.HTTP_200_OK
            )
        except Professional.DoesNotExist:
            return Response({"detail": "Professional not found."}, status=status.HTTP_404_NOT_FOUND)
        except Category.DoesNotExist:
            return Response({"detail": "Category not found."}, status=status.HTTP_404_NOT_FOUND)


class CertificateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        professional = request.user.professional
        serializer = CertificateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(professional=professional)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        try:
            certificate = Certificate.objects.get(id=pk, professional=request.user.professional)
        except Certificate.DoesNotExist:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CertificateSerializer(certificate, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            certificate = Certificate.objects.get(id=pk, professional=request.user.professional)
        except Certificate.DoesNotExist:
            return Response({"detail": "Certificate not found."}, status=status.HTTP_404_NOT_FOUND)

        certificate.delete()
        return Response({"detail": "Certificate deleted successfully."}, status=status.HTTP_204_NO_CONTENT)



class EducationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            professional = request.user.professional
            serializer = EducationSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                print('serializer is valid')
                serializer.save(professional=professional)
                print('professional saved',serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        try:
            professional = request.user.professional
            education = Education.objects.get(pk=pk, professional=professional)
            serializer = EducationSerializer(education, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Education.DoesNotExist:
            return Response({"detail": "Education not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        try:
            # Get the professional and the education record to delete
            professional = request.user.professional
            education = Education.objects.get(pk=pk, professional=professional)
            education.delete()
            return Response({"detail": "Education deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Education.DoesNotExist:
            return Response({"detail": "Education not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            professional = request.user.professional
            serializer = PortfolioSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.save(professional=professional)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk=None):
        try:
            professional = request.user.professional
            portfolio = Portfolio.objects.get(pk=pk, professional=professional)
            serializer = PortfolioSerializer(portfolio, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Portfolio.DoesNotExist:
            return Response({"detail": "Portfolio not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        try:
            # Get the professional and the portfolio record to delete
            professional = request.user.professional
            portfolio = Portfolio.objects.get(pk=pk, professional=professional)
            portfolio.delete()
            return Response({"detail": "Portfolio deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Portfolio.DoesNotExist:
            return Response({"detail": "Portfolio not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProfessionalVerificationRequestView(APIView):
    permission_classes = [IsAuthenticated]


    def post(self, request):
        user = request.user

        try:
            professional = Professional.objects.get(user=user)
        except Professional.DoesNotExist:
            return Response({"error": "You must be a professional to request verification."}, status=status.HTTP_403_FORBIDDEN)
        
        if professional.is_verified:
            return Response({"error": "You are already verified."}, status=status.HTTP_400_BAD_REQUEST)
        
        if VerificationRequest.objects.filter(professional=professional, status='pending').exists():
            return Response({"error": "A pending verification request already exists."}, status=status.HTTP_400_BAD_REQUEST)

        verification_request = VerificationRequest.objects.create(professional=professional)
        serializer = VerificationRequestSerializer(verification_request)

        return Response({"message": "Verification request submitted successfully.", "data": serializer.data}, status=status.HTTP_201_CREATED)


class ProfessionalSubscriptionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        professional = request.user.professional
        subscription_history = SubscriptionPlan.objects.filter(professional=professional)
        serializer = SubscriptionPlanSerializer(subscription_history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
    
class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        data = request.data
        amount = data.get("amount")
        plan_type = data.get("plan_type")
        duration = data.get("duration")
        print('duration',duration)
        return_url = data.get("return_url")
        txt_ref = uuid.uuid4()
        
        if not plan_type or not duration:
            return Response(
                {"error": "Plan type and duration are required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not amount:
            return Response(
                {"error": "Amount is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        professional = Professional.objects.filter(user=user, is_verified=True).first()
        if professional is None:
            return Response(
                {"error": "Professional not found or not verified."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Start a transaction block
        with transaction.atomic():
            # Check for active subscription
            active_subscription = SubscriptionPlan.objects.filter(
                professional=professional,
                start_date__lte=timezone.now(),
                end_date__gte=timezone.now()
            ).first()

            payment = None
            if active_subscription:
                payment = Payment.objects.filter(
                    professional=professional,
                    subscription_plan=active_subscription
                ).first()

                if payment and payment.payment_status == 'completed':
                    return Response(
                        {
                            "error": "You are already subscribed to an active plan.",
                            "plan_type": active_subscription.plan_type,
                            "duration": active_subscription.duration,
                            "end_date": active_subscription.end_date.isoformat(),
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Check if the professional has enough balance
            if professional.balance < amount:
                return Response(
                    {"error": "Insufficient balance, please deposit enough amount."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Proceed with payment initiation
            chapa_url = "https://api.chapa.co/v1/transaction/initialize"
            chapa_api_key = settings.CHAPA_SECRET_KEY
            payload = {
                "amount": amount,
                "currency": "ETB",
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "tx_ref": str(txt_ref),
                "return_url": f'{return_url}?transaction_id={txt_ref}'
            }
            headers = {
                "Authorization": f"Bearer {chapa_api_key}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(chapa_url, json=payload, headers=headers)
                if response.status_code == 200:
                    result = response.json()
                    # Create a Payment record
                    if active_subscription:
                        payment = Payment.objects.filter(
                            professional=professional,
                            subscription_plan=active_subscription).first()
                        if payment is not None  and payment.payment_status !='completed':
                            print('payment is updated')
                            payment.subscription_plan = active_subscription
                            payment.amount = amount
                            payment.transaction_id = str(txt_ref)
                            payment.payment_status = 'pending'
                            payment.save()
                        else:
                            payment = Payment.objects.create(
                                subscription_plan=active_subscription,
                                professional=professional,
                                transaction_id=str(txt_ref),
                                amount=amount,
                                payment_status='pending')
                            payment.save()
                    else: 
                        subscription_plan = SubscriptionPlan(
                            professional=professional,
                            plan_type=plan_type,
                            duration=duration
                        )
                        subscription_plan.save()
                        payment = Payment.objects.create(
                            subscription_plan=subscription_plan,
                            professional=professional,
                            transaction_id=str(txt_ref),
                            amount=amount,
                            payment_status='pending'
                        )
                        payment.save()
                
                    return Response(
                        {
                            "message": "Payment initiated successfully.",
                            "data": {
                                "payment_url": result.get("data", {}).get("checkout_url"),
                                "transaction_id": str(txt_ref)
                            }
                        },
                        status=status.HTTP_200_OK
                    )
                else:
                    error_message = response.json().get("message", "Failed to initiate payment.")
                    return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

            except requests.RequestException as e:
                return Response(
                    {"error": f"Payment request failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
class CheckPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, transaction_id):
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response(
                {"error": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        chapa_api_url = f"https://api.chapa.co/v1/transaction/verify/{transaction_id}"
        headers = {
            'Authorization': f'Bearer {settings.CHAPA_SECRET_KEY}',
        }
            
        try:
            response = requests.get(chapa_api_url, headers=headers)
            response_data = response.json()
            if response.status_code == 200:
                payment.payment_status = 'completed'
                payment.save()
                
                payment.professional.balance -= payment.amount
                payment.professional.is_available=True
                payment.professional.save()
                
                payment_data = PaymentSerializer(payment).data
                
                return Response({
                        "message": "Payment status checked successfully.",
                        "data":{
                            "payment":payment_data},
                            "first_name":response_data.get("data", {}).get("first_name"),
                            "last_name":response_data.get("data", {}).get("last_name"),
                            "email":response_data.get("data", {}).get("email"),
                            "amount":response_data.get("data", {}).get("amount"),
                            "currency":response_data.get("data", {}).get("currency")
                         },status=status.HTTP_200_OK)
            else:
                payment.payment_status ='failed'
                payment.save()
                return Response(
                    {"error": "Failed to retrieve payment status from Chapa."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except requests.exceptions.RequestException as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

       



            
 