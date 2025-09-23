# from datetime import datetime, timedelta, UTC
# from django.db import transaction
# from rest_framework import serializers
# from rest_framework.views import APIView
# from rest_framework import exceptions , status
# from django.contrib.auth.hashers import make_password
# from django.contrib.auth.password_validation import validate_password
# from django.core.exceptions import ValidationError as DjangoValidationError
# from rest_framework.response import Response
# from rest_framework.request import Request
# from rest_framework.permissions import (
#     IsAuthenticated,
#     IsAdminUser,
# )
# from common.pagination import CustomPagination
# from common.models import Company
# from accounts.models import (
#     User,
#     Apis,
#     Tools,
#     Roles,
# )
# from django.conf import settings
# from drf_spectacular.utils import extend_schema
# from drf_spectacular.types import OpenApiTypes

# class UserManagementListApiView(APIView):
#     """
#         GET: Return List of All Users
#         POST: Create a New User
#     """
#     permission_classes = [IsAdminUser]

#     class UserManagementListOutputSerializer(serializers.ModelSerializer):
#         class UserManagementListOutputRoles(serializers.ModelSerializer):
#             class Meta:
#                 model = Roles
#                 fields = ['id','title']
#         class UserManagementListOutputCompany(serializers.ModelSerializer):
#             class Meta:
#                 model = Company
#                 fields = ['id','name','typ','service_typ','code']
#         roles = UserManagementListOutputRoles()
#         company = UserManagementListOutputCompany()
#         class Meta:
#             model = User
#             fields = ['id','username','first_name_fa','last_name_fa','address',
#                       'first_name','last_name','email','is_staff','is_active','is_controller',
#                       'date_joined','last_login','is_active','roles','company']
            
#     class UserManagementListInputSerializer(serializers.ModelSerializer):
#         password = serializers.CharField(write_only=True, min_length=8)
#         confirm_password = serializers.CharField(write_only=True)
#         accessible_shrh_layers = serializers.ListField(
#             child=serializers.IntegerField(),
#             required=False,
#             allow_empty=True,
#         )

#         def validate_accessible_shrh_layers(self, value):
#             """
#             Validate that all provided ShrhLayer IDs exist
#             """
#             if value:
#                 from contracts.models.SharhKhadamats import ShrhLayer
#                 existing_ids = ShrhLayer.objects.filter(id__in=value).values_list('id', flat=True)
#                 invalid_ids = set(value) - set(existing_ids)
                
#                 if invalid_ids:
#                     raise serializers.ValidationError(
#                         f"لایه‌های با شناسه‌های {list(invalid_ids)} یافت نشدند"
#                     )
#             return value

#         def validate_password(self, password):
#             """
#             Validate password using Django's password validators from settings
#             """
#             try:
#                 # This will use your CustomPasswordValidator from settings
#                 validate_password(password)
#             except DjangoValidationError as e:
#                 # Convert Django validation errors to DRF format
#                 raise serializers.ValidationError(e.messages)
#             return password
#         def validate(self, attrs):
#             """
#             Validate that password and confirm_password match
#             """
#             password = attrs.get('password')
#             confirm_password = attrs.get('confirm_password')
            
#             if password != confirm_password:
#                 raise serializers.ValidationError({
#                     'confirm_password': 'رمز عبور و تکرار آن باید یکسان باشند'
#                 })
            
#             # Remove confirm_password from validated data as it's not needed for saving
#             attrs.pop('confirm_password', None)
#             return attrs
#         def create(self, validated_data):
#             """
#             Create user with hashed password
#             """
#             # Hash the password before saving
#             password = validated_data.get('password')
#             if password:
#                 validated_data['password'] = make_password(password)
            
#             return super().create(validated_data)
#         class Meta:
#             model = User
#             fields = ['username','first_name_fa','last_name_fa','address','accessible_shrh_layers','is_controller'
#                       'first_name','last_name','email','roles','password','confirm_password','company']
    
            

#     def get(self, request: Request) -> Response:
#         try:
#             all_users = User.objects.all()
#             paginator = CustomPagination()
#             paginated_queryset = paginator.paginate_queryset(all_users, request)
#             serializer = self.UserManagementListOutputSerializer(paginated_queryset , many=True)
#             return paginator.get_paginated_response(serializer.data)
#         except Exception as e:                      
#             print(f"Error in UserManagementListApiView: {e}")
#             return Response(
#                 {"detail": "خطا در خواندن لیست کاربر ها"}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
        
#     def post(self, request:Request) -> Response:
#         try:
#             serializer = self.UserManagementListInputSerializer(data=request.data)
#             if not serializer.is_valid():
#                 return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

#             user = serializer.save()
#             # Delay sync until after current transaction commits
#             # user.sync_accessible_contracts()
            
#             # Return the created user data using output serializer
#             output_serializer = self.UserManagementListOutputSerializer(user)
#             return Response(output_serializer.data,status=status.HTTP_201_CREATED)
            
#         except Exception as e:                      
#             print(f"Error in UserManagementListApiView: {e}")
#             return Response(
#                 {"detail": "خطا در ساخت کاربر جدید"}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
        
# class UserManagementDetailsApiView(APIView):
#     """
#         GET: Return List of All Users
#         POST: Create a New User
#     """
#     permission_classes = [IsAdminUser]

#     class UserManagementtDetailsOutputSerializer(serializers.ModelSerializer):
#         class UserManagementtDetailsOutputRoles(serializers.ModelSerializer):
#             class Meta:
#                 model = Roles
#                 fields = ['id','title']
#         class UserManagementtDetailsOutputSharhLayer(serializers.ModelSerializer):
#             class UserManagementListOutputSharhLayerLayerName(serializers.ModelSerializer):
#                 class Meta:
#                     from layers.models.models import LayersNames
#                     model = LayersNames
#                     fields = ['dtyp','lyrgroup_en','lyrgroup_fa','layername_en','layername_fa','geometrytype']
#             layer_name = UserManagementListOutputSharhLayerLayerName()
#             class Meta:
#                 from contracts.models.SharhKhadamats import ShrhLayer
#                 model = ShrhLayer
#                 fields = '__all__'
#         class UserManagementDetailsOutputCompany(serializers.ModelSerializer):
#             class Meta:
#                 model = Company
#                 fields = ['id','name','typ','service_typ','code']


#         roles = UserManagementtDetailsOutputRoles()
#         accessible_shrh_layers = UserManagementtDetailsOutputSharhLayer(many=True)
#         company = UserManagementDetailsOutputCompany()
        
#         class Meta:
#             model = User
#             fields = ['id','username','first_name_fa','last_name_fa','address',
#                       'first_name','last_name','email','is_staff','is_active','is_controller',
#                       'date_joined','last_login','is_active','roles','accessible_shrh_layers','company']
                      
#     class UserManagementDetailsInputSerializer(serializers.ModelSerializer):
#         accessible_shrh_layers = serializers.ListField(
#             child=serializers.IntegerField(),
#             required=False,
#             allow_empty=True,
#         )
#         def validate_accessible_shrh_layers(self, value):
#             """
#             Validate that all provided ShrhLayer IDs exist
#             """
#             if value:
#                 from contracts.models.SharhKhadamats import ShrhLayer
#                 existing_ids = ShrhLayer.objects.filter(id__in=value).values_list('id', flat=True)
#                 invalid_ids = set(value) - set(existing_ids)
                
#                 if invalid_ids:
#                     raise serializers.ValidationError(
#                         f"لایه‌های با شناسه‌های {list(invalid_ids)} یافت نشدند"
#                     )
#             return value
#         def update(self, instance, validated_data):
#             """
#             Update user instance with accessible_shrh_layers
#             """
#             # Extract accessible_shrh_layers from validated_data
#             accessible_shrh_layers_ids = validated_data.pop('accessible_shrh_layers', None)
            
#             # Update regular fields
#             for attr, value in validated_data.items():
#                 setattr(instance, attr, value)
            
#             instance.save()
            
            
#             # Update the many-to-many relationship if provided
#             if accessible_shrh_layers_ids is not None:
#                 instance.accessible_shrh_layers.set(accessible_shrh_layers_ids)
            
#             return instance
#         class Meta:
#             model = User
#             fields = ['username','first_name_fa','last_name_fa','address','accessible_shrh_layers',
#                       'is_controller','first_name','last_name','email','roles','company']                  

#     def get(self , request: Request , userid:int) -> Response:
#         try:
#             user_instance = User.objects.get(pk = userid)
#             serializer = self.UserManagementtDetailsOutputSerializer(user_instance)
#             return Response(serializer.data , status=status.HTTP_200_OK)
#         except User.DoesNotExist:
#             return Response(
#                 {"detail": "کاربر با این آیدی پیدا نشد"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:                      
#             print(f"Error in UserManagementDetailsApiView: {e}")
#             return Response(
#                 {"detail": "خطا در خواندن کاربر"}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
        
#     def put(self , request: Request , userid:int) -> Response:
#         try:
#             user_instance = User.objects.get(pk=userid)
            
#             # Serialize the incoming data
#             serializer = self.UserManagementDetailsInputSerializer(
#                 user_instance, 
#                 data=request.data, 
#                 partial=True  # Allow partial updates
#             )
            
#             if not serializer.is_valid():
#                 return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

#             # Update the user
#             updated_user = serializer.save()
#             # updated_user.sync_accessible_contracts()
            
#             output_serializer = self.UserManagementtDetailsOutputSerializer(updated_user)
#             return Response(output_serializer.data,status=status.HTTP_200_OK)

#         except User.DoesNotExist:
#             return Response(
#                 {"detail": "کاربر با این آیدی پیدا نشد"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:                      
#             print(f"Error in UserManagementDetailsApiView: {e}")
#             return Response(
#                 {"detail": "خطا در ویرایش کاربر"}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
    
#     def delete(self , request: Request , userid:int) -> Response:
#         try:
#             user_instance = User.objects.get(pk = userid)
#             user_instance.delete()
#             return Response(status=status.HTTP_204_NO_CONTENT)
#         except User.DoesNotExist:
#             return Response(
#                 {"detail": "کاربر با این آیدی پیدا نشد"}, 
#                 status=status.HTTP_404_NOT_FOUND
#             )
#         except Exception as e:                      
#             print(f"Error in UserManagementDetailsApiView: {e}")
#             return Response(
#                 {"detail": "خطا در حذف کاربر"}, 
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )