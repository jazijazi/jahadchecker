from datetime import datetime, timedelta, UTC
from django.utils import timezone
from django.db import transaction
from typing import Tuple
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework import exceptions , status
from rest_framework.response import Response
from rest_framework.request import Request
from accounts.tokenization import create_access_token , create_refresh_token ,decode_refresh_token
from rest_framework.permissions import (
    IsAuthenticated
)
from django.db.models import Q , Prefetch

from accounts.models import (
    User,
    Apis,
    Tools,
    Roles,
    Notification,
)
from common.models import Province , Company
from common.pagination import CustomPagination

from django.conf import settings
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from captcha.services import CaptchaService


class LoginUser(APIView):
    """
    API view for user authentication and token generation.
    """
    permission_classes = []
    authentication_classes = []

    class LoginInputSerializer(serializers.Serializer):
        username = serializers.CharField(
            max_length=150,
            help_text="نام کاربری",
            required=True,
            error_messages={
                'required': 'نام کاربری الزامی است',
                'blank': 'نام کاربری نمی‌تواند خالی باشد',
                'max_length': 'نام کاربری نمی‌تواند بیشتر از ۱۵۰ کاراکتر باشد'
            }
        )
        password = serializers.CharField(
            max_length=128,
            help_text="رمز عبور",
            required=True,
            style={'input_type': 'password'},
            error_messages={
                'required': 'رمز عبور الزامی است',
                'blank': 'رمز عبور نمی‌تواند خالی باشد',
                'max_length': 'رمز عبور نمی‌تواند بیشتر از ۱۲۸ کاراکتر باشد'
            }
        )
        rememberMe = serializers.BooleanField(
            default=False,
            required=False,
            help_text="مرا به خاطر بسپار"
        )
        captcha_id = serializers.CharField(
            max_length=150,
            help_text="نام کاربری",
            required=True,
            error_messages={
                'required': 'شناسه کپچا الزامی است',
                'blank': 'شناسه کپچا نمی‌تواند خالی باشد',
                'max_length': 'شناسه کپچا نمی‌تواند بیشتر از ۱۵۰ کاراکتر باشد'
            }
        )
        captcha_answer = serializers.CharField(
            max_length=150,
            help_text="نام کاربری",
            required=True,
            error_messages={
                'required': 'شناسه کپچا الزامی است',
                'blank': 'شناسه کپچا نمی‌تواند خالی باشد',
                'max_length': 'پاسخ کپچا نمی‌تواند بیشتر از ۱۵۰ کاراکتر باشد'
            }
        )
    class LoginOutputSerializer(serializers.Serializer):
        token = serializers.CharField()
        user = serializers.DictField(
            help_text="اطلاعات کاربر",
            child=serializers.CharField(),
            allow_empty=False
        )
    
    @extend_schema(
        request=LoginInputSerializer,
        responses={
            200: LoginOutputSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        description="Authenticate user and return JWT tokens in response and refresh token in cookie.",
        tags=["ACCOUNTS"]
    )
    def post(self, request: Request) -> Response:
        """
        Authenticate user and generate access and refresh tokens.
        
        Request body:
        - username: User's username
        - password: User's password
        - rememberMe: Boolean flag for extended session
        
        """
        try:
            serializer = self.LoginInputSerializer(data=request.data)
            
            if not serializer.is_valid():
                return Response(
                    {'detail': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            validated_data = serializer.validated_data
            username = validated_data['username']
            password = validated_data['password']
            remember_me = validated_data.get('rememberMe', False)
            
            #Only in Not Debug Mode validate the captcha
            if not settings.DEBUG:
                captch_result, captch_result_message = self._validate_captcha(
                    captcha_id =  validated_data['captcha_id'],
                    captcha_answer = validated_data['captcha_answer'],
                )

                if not captch_result:
                    return Response({"detail":captch_result_message} , status=status.HTTP_400_BAD_REQUEST)
            
            # Get user by username - use get_user_by_username helper for flexibility
            user = self._get_user_by_username(username)
            
            # Authenticate user
            if not user or not user.check_password(password):
                raise exceptions.AuthenticationFailed(detail='نام کاربری یا رمز عبور اشتباه است')
            
            if not user.is_active:
                raise exceptions.AuthenticationFailed('اکانت شما موقتاً غیرفعال شده است لطفا با پشتیبانی تماس بگیرید')
            
            # Update last login time
            # user.last_login = datetime.now(UTC)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
                        
            # Create tokens
            access_token = create_access_token(user_id=user.id, expires_in_seconds=9000)
            refresh_token = create_refresh_token(user_id=user.id, expires_in_days=7)
            
            # Prepare response
            response_data = {
                'token': access_token,
                'user': self._get_user_info(user),
            }

            response_serializer = self.LoginOutputSerializer(data=response_data)
            if response_serializer.is_valid():
                response = Response(response_serializer.validated_data)
            else:
                # Fallback to original data if serializer validation fails
                response = Response(response_data)
            
            # Set refresh token cookie
            cookie_max_age = timedelta(days=7).total_seconds() if remember_me else None
            self._set_refresh_token_cookie(response=response, refresh_token=refresh_token, max_age=cookie_max_age)
            
            return response
            
        except exceptions.AuthenticationFailed as e:
            return Response({"detail":str(e)},status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            print(e)
            return Response(
                {'detail': 'خطا در ورود به سیستم. لطفا مجددا تلاش کنید'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _validate_captcha(self , captcha_id: str , captcha_answer: str) -> Tuple[bool, str]:
        return CaptchaService.validate_captcha(
            key=captcha_id,
            user_response=captcha_answer,
        )

    
    def _get_user_by_username(self, username: str) -> User:
        
        return User.objects.filter(username=username).first()
    
    def _get_user_info(self, user: User) -> dict:
        """
        Return user information to include in response.
        """
        return {
            'id': user.id,
            'username': user.username,
        }
    
    def _set_refresh_token_cookie(self, response: Response, refresh_token: str, max_age: int = None) -> None:
        """
        Set the refresh token cookie.
        """        
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,  # Not accessible via JavaScript
            max_age=max_age,
        )


class RefreshToken(APIView):
    permission_classes = []
    authentication_classes = []

    class RefreshTokenResponseSerializer(serializers.Serializer):
        token = serializers.CharField(help_text="New access token")
  
    @extend_schema(
        request=None,
        responses={
            200: RefreshTokenResponseSerializer,
            400: OpenApiTypes.OBJECT,
        },
        description="Get the RefreshToken from cookie of user and if available return a new AccessToken",
        tags=["ACCOUNTS"]
    )
    def post(self, request:Request)->Response:
        try:
            refresh_token = request.COOKIES.get('refresh_token')
            user_id = decode_refresh_token(refresh_token)
            new_access_token = create_access_token(user_id=user_id, expires_in_seconds=9000)

            return Response({
                'token': new_access_token    
            })

        except Exception as e:
            return Response(
                {'detail': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class LogoutUser(APIView): 
  permission_classes = [IsAuthenticated]

  class LogoutResponseSerializer(serializers.Serializer):
        detail = serializers.CharField(help_text="پیام تایید خروج")
  
  @extend_schema(
        responses={
            200: LogoutResponseSerializer,
            401: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        description="Logout for clean Refresh Token From user request cookie",
        tags=["ACCOUNTS"]
    )
  def post(self, request:Request) -> Response:

    #TODO: add access token to blocklist token lists in redis or in database and check it in auth
    response = Response()
    response_data = self.LogoutResponseSerializer({
        'detail': 'خروج با موفقیت انجام شد'
    })
    response.delete_cookie(key='refresh_token')    
    response.data = response_data.data
    response.status_code = status.HTTP_200_OK
    return response
  
class UserProfile(APIView):
    permission_classes = [IsAuthenticated]
    """
    Authenticated user get and update their own profile
    GET: Retrieve user profile data
    PUT: Update user profile data
    """
    class UserProfileInputSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = [
                "first_name","last_name",
                "first_name_fa","last_name_fa",
                "address","email",
            ]

    class UserProfileOutputSerializer(serializers.ModelSerializer):
        class UserProfileOutputSerializerRoles(serializers.ModelSerializer):
            class UserProfileOutputSerializerRolesApis(serializers.ModelSerializer):
                class Meta:
                    model = Apis
                    fields = ['id' , 'method' , 'url' , 'desc']
            class UserProfileOutputSerializerRolesTools(serializers.ModelSerializer):
                class Meta:
                    model = Tools
                    fields = ['id' , 'title' , 'desc']
            apis = UserProfileOutputSerializerRolesApis(many=True)
            tools = UserProfileOutputSerializerRolesTools(many=True)
            class Meta:
                model = Roles
                fields = ['id' , 'apis' , 'tools' , 'title' , 'desc']

        class UserProfileOutputSerializerCompany(serializers.ModelSerializer):
            class Meta:
                model = Company
                fields = ['id','name','typ','service_typ','code']
        roles = UserProfileOutputSerializerRoles()
        company = UserProfileOutputSerializerCompany()
        class Meta:
            model = User
            fields = [
                "username","first_name","last_name",
                "first_name_fa","last_name_fa",
                "address","email","last_login",'is_controller',
                "is_staff","is_superuser","roles","company",
            ]

    @extend_schema(
        responses={
            200:UserProfileOutputSerializer,
            401:OpenApiTypes.OBJECT,
            404:OpenApiTypes.OBJECT,
            500:OpenApiTypes.OBJECT
        },
        description="Get authenticated user's profile.",
        tags=["ACCOUNTS"]
    )
    def get(self , request:Request) -> Response:
        try:
            user = request.user
            if not user or not user.is_authenticated:
                raise Exception("کاربر نامعتبر است")
            
            serialized_data = self.UserProfileOutputSerializer(user)
            return Response(serialized_data.data,status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({"detail":"کاربر یافت نشد"},status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"detail":"خطا در دریافت مشخصات کاربر"},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @extend_schema(
        request=UserProfileInputSerializer,
        responses={
            200:UserProfileOutputSerializer,
            401:OpenApiTypes.OBJECT,
            404:OpenApiTypes.OBJECT,
            500:OpenApiTypes.OBJECT,
        },
        description="Update authenticated user own profile.",
        tags=["ACCOUNTS"]
    )
    def put(self, request:Request) -> Response:
        try:
            with transaction.atomic():
                user = request.user
                if not user or not user.is_authenticated:
                    raise Exception("کاربر نامعتبر است")
                
                serializer = self.UserProfileInputSerializer(user, data=request.data, context={'request': request}, partial=True)
                
                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                serializer.save()

                updated_data = self.UserProfileOutputSerializer(user)
                return Response(updated_data.data, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({"detail":"کاربر یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"detail":"خطا در بروزرسانی مشخصات کاربر"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class Register(APIView):
    """
    Register new users with validation data
    Uses CustomPasswordValidator from validators.py for validate the password

    After a successful registration, the user is Automatically logged in.
    """
    permission_classes = []
    authentication_classes = []

    class RegisterOutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = User
            fields = [
                "username","first_name","last_name",
                "first_name_fa","last_name_fa",
                "address","email","last_login",
                "is_staff","is_superuser",
            ]

    class RegisterInputSerializer(serializers.ModelSerializer):
        password = serializers.CharField(write_only=True, required=True)
        confirm_password = serializers.CharField(write_only=True, required=True)
        
        class Meta:
            model = User
            fields = [
                "username", "email", "password", "confirm_password",
                "first_name", "last_name", "first_name_fa", "last_name_fa", 
                "address"
            ]
        
        def validate(self, data):
            # Check if passwords match
            if data.get('password') != data.get('confirm_password'):
                raise serializers.ValidationError({"confirm_password": "رمز عبور و تکرار آن مطابقت ندارند"})
            
            # Apply custom password validation
            try:
                # Import auth password validators from settings
                from django.contrib.auth.password_validation import validate_password
                # This will use your CustomPasswordValidator from settings.AUTH_PASSWORD_VALIDATORS
                validate_password(data.get('password'))
            except Exception as e:
                raise serializers.ValidationError({"password": e.messages})
                
            return data


    @extend_schema(
        request=RegisterInputSerializer,
        responses={
            200: RegisterOutputSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
        },
        description="Register New User",
        tags=["ACCOUNTS"]
    )
    def post(self, request:Request) -> Response:
        try:
            with transaction.atomic():
                serializer = self.RegisterInputSerializer(data=request.data)

                if not serializer.is_valid():
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

                validated_data = serializer.validated_data

                # Remove confirm_password from data before creating user
                validated_data.pop('confirm_password')

                # Create user with validated data
                password = validated_data.pop('password')
                user = User.objects.create(**validated_data)
                user.set_password(password)  # Set password securely (hashed)
                user.save()

                access_token = create_access_token(user_id=user.id, expires_in_seconds=9000)
                
                response = Response({
                    "token": access_token,
                    "detail": self.RegisterOutputSerializer(user).data
                }, status=status.HTTP_201_CREATED)
                
                refresh_token = create_refresh_token(user_id=user.id, expires_in_days=7)
                self._set_refresh_token_cookie(response=response, refresh_token=refresh_token, max_age=None)

                return response
        
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در ثبت نام کاربر"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def _set_refresh_token_cookie(self, response: Response, refresh_token: str, max_age: int = None) -> None:
        """
        Set the refresh token cookie.
        """        
        response.set_cookie(
            key='refresh_token',
            value=refresh_token,
            httponly=True,  # Not accessible via JavaScript
            max_age=max_age,
        )

class NotificationListApiViews(APIView):
    """
        Send a List of Notifications for user
    """
    permission_classes = [IsAuthenticated]

    class NotificationListOutputSerializer(serializers.ModelSerializer):
        class NotificationListOutputSerializerUser(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = ['id','username']

        sender = NotificationListOutputSerializerUser()

        class Meta:
            model = Notification
            fields = ['id','sender','subject','is_read','created_at']

    def get(self, request:Request) -> Response:
        try:
            user = request.user
            all_related_notif_to_user = Notification.objects.filter(receiver=user)     
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_related_notif_to_user, request)
            serializer = self.NotificationListOutputSerializer(paginated_queryset,many=True,context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در خواندن اعلان‌های مربوط به کاربر"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NotificationDetailsApiViews(APIView):
    """
        GET: Retrive a Notification with detail fields
        Delete: Delete A Notification Instance
    """
    permission_classes = [IsAuthenticated]

    class NotificationDetailsOutputSerializer(serializers.ModelSerializer):
        class NotificationDetailsOutputSerializerUser(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = ['id','username','first_name','last_name','email']

        sender = NotificationDetailsOutputSerializerUser()

        class Meta:
            model = Notification
            fields = ['id','sender','subject','is_read','text','created_at']

    def get(self, request:Request, notifid:int) -> Response:
        try:
            thisuser = request.user
            notif_instance = Notification.objects.get(pk=notifid)     
            if notif_instance.receiver != thisuser:
                raise Exception("user not allow to see this notif")
            serialzied_notif = self.NotificationDetailsOutputSerializer(notif_instance)
            notif_instance.is_read = True
            notif_instance.save()
            return Response(serialzied_notif.data , status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"detail": "اعلان مورد نظر یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در خواندن اعلان‌"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self, request:Request, notifid:int) -> Response:
        try:
            user = request.user
            notif_instance = Notification.objects.get(pk=notifid)     
            if notif_instance.receiver != request.user:
                raise Exception("user not allow to see this notif")
            notif_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response({"detail": "اعلان مورد نظر یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"detail": "خطا در حذف اعلان‌"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
