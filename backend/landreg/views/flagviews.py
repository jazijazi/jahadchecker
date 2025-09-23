import uuid
from typing import cast, Dict, Any
from django.core.validators import FileExtensionValidator
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import serializers
from rest_framework.permissions import AllowAny , IsAdminUser
from common.pagination import CustomPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.urls import reverse
from django.db import transaction
from django.contrib.gis.geos import MultiPolygon
from django.db import IntegrityError
from landreg.services.gis import process_pelak_border
from landreg.models.flag import Flag
from landreg.models.cadaster import Cadaster
from common.models import Company , Province
from accounts.models import User


class FlagListApiView(APIView):
    """
        GET: get all flags on a cadaster
        POST: create new falg on a cadaster
    """
    class FlagListOutputSerializer(serializers.ModelSerializer):
        class FlagListOurputSerializerUser(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = ['username' , 'first_name_fa','last_name_fa']

        class FlagListOurputSerializerCadaster(serializers.ModelSerializer):
            class Meta:
                model = Cadaster
                fields = ['id','uniquecode','jaam_code']

        createdby = FlagListOurputSerializerUser()
        cadaster = FlagListOurputSerializerCadaster()
        class Meta:
            model = Flag
            fields = ['id', 'createdby' , 'description' , 'cadaster' , 'status']

    class FlagListInputSerializer(serializers.Serializer):
        latitude = serializers.FloatField(
            required=True,
            error_messages={
                "required": "عرض جغرافیایی اجباری است",
            },
        )
        longitude = serializers.FloatField(
            required=True,
            error_messages={
                "required": "طول جغرافیایی اجباری است",
            },
        )
        description = serializers.CharField(
            required=False,
            allow_blank=True,
            allow_null=True,
            max_length=512,
            help_text="توضیحات اضافی در مورد فلگ"
        )
        status = serializers.ChoiceField(
            choices=Flag.FLAG_STATUS_CHOICES,
            required=True,
            help_text="وضعیت فلگ"
        )

        def validate_latitude(self, value):
            """Validate latitude is within valid range"""
            if not (-90 <= value <= 90):
                raise serializers.ValidationError("عرض جغرافیایی باید بین -90 تا 90 باشد")
            return value

        def validate_longitude(self, value):
            """Validate longitude is within valid range"""
            if not (-180 <= value <= 180):
                raise serializers.ValidationError("طول جغرافیایی باید بین -180 تا 180 باشد")
            return value

    
    def _check_user_permissions(self, user: User) -> tuple[bool, str]:
        """Check if user has permission to create pelak"""
        if user.is_superuser:
            return True, ""
        
        if not user.company:
            return False, "کاربر بدون شرکت است"
        
        if not (user.company.is_nazer or user.company.is_supernazer):
            return False, "شما اجازه بارگذاری پلاک جدید را ندارید"
        
        return True, ""

    def get(self, request: Request , cadasterid:int) -> Response:
        try:
            user:User = request.user
            
            has_permission, error_msg = self._check_user_permissions(user)
            if not has_permission:
                return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)
            
            cadaster_instance = Cadaster.objects.get(pk=cadasterid)
            all_flags = Flag.objects.filter(cadaster=cadaster_instance)
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_flags, request)
            serializer = self.FlagListOutputSerializer(paginated_queryset,many=True,context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        except Cadaster.DoesNotExist:
            return Response(
                {"detail": "کاداستری با این آیدی یافت نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error creating pelak: {str(e)}")
            return Response(
                {"detail": "خطا در خواندن لیست فلگ ها"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def post(self, request: Request , cadasterid:int) -> Response:
        try:
            user:User = request.user
            
            has_permission, error_msg = self._check_user_permissions(user)
            if not has_permission:
                return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)
            
            # Check if cadaster exists
            try:
                cadaster_instance = Cadaster.objects.get(pk=cadasterid)
            except Cadaster.DoesNotExist:
                return Response(
                    {"detail": "کاداستری با این آیدی یافت نشد"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Validate input data
            serializer = self.FlagListInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            validated_data = cast(Dict[str, Any], serializer.validated_data)
            
            # Create Point geometry from latitude and longitude
            from django.contrib.gis.geos import Point
            point = Point(
                validated_data['longitude'], 
                validated_data['latitude'], 
                srid=4326
            )
            
            # Create the flag
            flag = Flag.objects.create(
                border=point,
                createdby=user,
                description=validated_data.get('description', ''),
                cadaster=cadaster_instance,
                status=validated_data.get('status')
            )
            
            # Return the created flag data
            output_serializer = self.FlagListOutputSerializer(flag, context={'request': request})
            
            return Response(
                {
                    "detail": "فلگ با موفقیت ایجاد شد",
                    "flag": output_serializer.data
                }, 
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            print(f"Error creating pelak: {str(e)}")
            return Response(
                {"detail": "خطا در خواندن لیست فلگ ها"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 