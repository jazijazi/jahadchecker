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
from landreg.models.pelak import Pelak
from common.models import Company , Province
from accounts.models import User


class PelakListApiViews(APIView):
    """
        TODO: GET: return all pelaks
        POST: create new Plak Instance
    """

    class PelakListInputSerializer(serializers.Serializer):
        file = serializers.FileField(
            required=True,
            allow_null=False,  # Changed from True to False since it's required
            error_messages={
                "required": "این فیلد اجباری است",
            },
            validators=[
                FileExtensionValidator(
                    allowed_extensions=['zip'],
                    message="فایل محدوده حتما باید با فرمت zip باشد"
                )
            ])
        province_selected_id = serializers.IntegerField(
            required=False,
            allow_null=True,  # Allow null for non-superusers
        )

        def validate_province_selected_id(self, value):  # Fixed method name
            if value is None:
                return value
            try:
                Province.objects.get(pk=value)
                return value
            except Province.DoesNotExist:
                raise serializers.ValidationError("استانی با این آیدی یافت نشد")

        def validate(self, data):
            """Cross-field validation"""
            request = self.context.get('request')
            if request and request.user.is_superuser:
                if not data.get('province_selected_id'):
                    raise serializers.ValidationError({
                        'province_selected_id': 'کاربر ادمین باید استان را مشخص کند'
                    })
            return data

    def _check_user_permissions(self, user: User) -> tuple[bool, str]:
        """Check if user has permission to create pelak"""
        if user.is_superuser:
            return True, ""
        
        if not user.company:
            return False, "کاربر بدون شرکت است"
        
        if not user.company.is_nazer:
            return False, "شما اجازه بارگذاری پلاک جدید را ندارید"
        
        return True, ""

    def _get_province_for_user(self, user: User, province_id: int|None = None) -> tuple[Province|None, str]:
        """Get appropriate province based on user type"""
        if user.is_superuser:
            try:
                return Province.objects.get(pk=province_id), ""
            except Province.DoesNotExist:
                return None, "استان یافت نشد"
        else:
            # For nazer companies
            province = user.company.provinces.first()
            if not province:
                return None, "شرکت شما به هیچ استانی متصل نیست"
            return province, ""

    def post(self, request: Request) -> Response:
        """
            Only Nazer and Superuser can create
        """
        # Check permissions first
        has_permission, error_msg = self._check_user_permissions(request.user)
        if not has_permission:
            return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)

        # Validate input data
        serializer = self.PelakListInputSerializer(
            data=request.data, 
            context={'request': request}  # Pass request for cross-field validation
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            validated_data = cast(Dict[str, Any], serializer.validated_data)
            user: User = request.user

            # Get appropriate province
            province_instance, error_msg = self._get_province_for_user(
                user, 
                validated_data.get('province_selected_id')
            )
            if not province_instance:
                return Response({"detail": error_msg}, status=status.HTTP_400_BAD_REQUEST)

            zip_file = validated_data['file']

            # Process the zip file
            res, result_data, message = process_pelak_border(zipfile_obj=zip_file)
            if not res:
                return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

            # Create pelaks in bulk for better performance
            pelak_objects = []
            for plk in result_data:
                pelak_objects.append(Pelak(
                    title=plk["title"],
                    number=plk["number"],
                    created_by=user,
                    border=MultiPolygon(plk["border"]),
                    provinces=province_instance
                ))
            
            # Use bulk_create for better performance
            try:
                Pelak.objects.bulk_create(pelak_objects)
                return Response(
                    {"detail": f"تعداد {len(pelak_objects)} پلاک با موفقیت بارگذاری شد"}, 
                    status=status.HTTP_201_CREATED
                )
            except IntegrityError:
                return Response(
                    {"detail": "برخی از شماره پلاک‌ها تکراری است"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            print(f"Error creating pelak: {str(e)}")
            return Response(
                {"detail": "خطا در ساخت پلاک جدید"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



