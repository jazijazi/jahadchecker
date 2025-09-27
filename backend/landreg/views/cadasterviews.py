import zipfile
from django.utils import timezone
from typing import cast, Dict, Any , List
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
from landreg.services.gis import (
    process_pelak_border,
    process_gdb_file,
) 
from landreg.exceptions import GeoDatabaseValidationError
from landreg.models.flag import Flag
from landreg.models.cadaster import Cadaster , OldCadasterData
from common.models import Company , Province
from accounts.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile
from landreg.services.gis import drop_table_if_exists


class UploadOldCadasterApiView(APIView):
    """
        1. upload oldcadaster data as a geodatabase !
        2. get layers from geodatabase and save them to postgres as a new table for each layer
        3. save the tablename (and other data) in OldCadasterData
        *** only user.issuperuser and user.company.is_nazer can use this api
    """

    class UploadOldCadasterInputSerializer(serializers.Serializer):
        gdbzipfile = serializers.FileField(required=True,
            help_text="ZIP file containing the gdb file",
            error_messages={
                'required': "این فیلد اجباری است",
                'blank': "این فیلد نمیتواند خالی باشد.",
                'null': "این فیلد نمیتواند null باشد."
            })
        
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
          
        def validate_gdbzipfile(self,value):
            if not zipfile.is_zipfile(value):
                raise serializers.ValidationError("فایل باید از نوع ZIP باشد.")
            
    class UploadOldCadasterOutputSerializer(serializers.ModelSerializer):
        
        class Meta:
            model = OldCadasterData
            fields = ['id','table_name','status']


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
            

    def post(self, request:Request) -> Response:
        try:
            user:User = request.user
            
            has_permission, error_msg = self._check_user_permissions(user)
            if not has_permission:
                return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)
            
            input_serializer = self.UploadOldCadasterInputSerializer(data=request.data)
            if not input_serializer.is_valid():
                return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            validated_data = cast(Dict[str, Any], input_serializer.validated_data)
            
            # Get province for user 
            province_instance, error_msg = self._get_province_for_user(
                user, 
                validated_data.get('province_selected_id')
            )
            if not province_instance:
                return Response({"detail": error_msg}, status=status.HTTP_400_BAD_REQUEST)
            
            gdbzipfile:InMemoryUploadedFile = request.FILES['gdbzipfile']  # type: ignore
            
            from landreg.services.gis import ProcessResult
            result:List[ProcessResult] = process_gdb_file(gdbzipfile=gdbzipfile)
            
            created_oldcadasterdata : List[OldCadasterData] = []

            for res in result:
                oldcadasterdata_new_instance = OldCadasterData.objects.create(
                    table_name = res["table_name"],
                    created_by = user,
                    province = province_instance,
                )
                created_oldcadasterdata.append(oldcadasterdata_new_instance)

            output_serializer = self.UploadOldCadasterOutputSerializer(created_oldcadasterdata,many=True)
            return Response(output_serializer.data , status=status.HTTP_201_CREATED)

        except GeoDatabaseValidationError as gdderr:
            return Response({"detail": f"{str(gdderr)}"}, status=status.HTTP_400_BAD_REQUEST)

            
        except Exception as e:
            print(f"Error creating pelak: {str(e)}")
            return Response(
                {"detail": "خطا در بارگذاری دیتای قدیمی "}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 
        
# class OldCadasterListApiView(APIView):
        # Object level permission
        # - superuser and supernazer get all
        # - nazer and mohaver get only thoes in same proviance

class OldCadasterDetailsApiView(APIView):
    """
        Object level permission
        - check user superuser or supernazer or user.company.provinace.first equal to oldcadaster.proviance 

        GET: get the oldcadasterdata with details
        DELETE: delete a oldcadasterdata 
    
    """

    class OldCadasterDetailsOutputSerializer(serializers.ModelSerializer):

        class OldCadasterDetailsOutputSerializerUser(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = ['id','username','first_name_fa','last_name_fa']
        class OldCadasterDetailsOutputSerializerProvince(serializers.ModelSerializer):
            class Meta:
                model = Province
                fields = ['id','name_fa']
 
        province = OldCadasterDetailsOutputSerializerProvince()
        created_by = OldCadasterDetailsOutputSerializerUser()
        matched_by = OldCadasterDetailsOutputSerializerUser()
        class Meta:
            model = OldCadasterData
            fields = ['table_name','created_by','status',
                      'matched_by','matched_at','province',]

    def _check_user_permissions(self, user: User, oldcadasterdata_instance: OldCadasterData) -> tuple[bool, str]:
        """Check if user has permission to access this OldCadasterData"""
        # Superuser has access to everything
        if user.is_superuser:
            return True, ""
        
        # Check if user has a company
        if not user.company:
            return False, "کاربر بدون شرکت است"
        
        # Super nazer has access to everything
        if user.company.is_supernazer:
            return True, ""
        
        # Mohaver can only access data from their province
        if user.company.is_moshaver or user.company.is_nazer:
            if not user.company.provinces.exists():
                return False, "شرکت شما فاقد استان است"
            
            user_province = user.company.provinces.first()
            if user_province != oldcadasterdata_instance.province:
                return False, "شما فقط به دیتای استان خودتان دسترسی دارید"
            
            return True, ""
        
        # If none of the above conditions are met
        return False, "شما اجازه دسترسی به این دیتا را ندارید"
    
    def get(self , request:Request , oldcadasterid:int) -> Response:
        try:
            user:User = request.user
            oldcadasterdata_instance = OldCadasterData.objects.get(pk=oldcadasterid)

            # Check permissions
            has_permission, error_msg = self._check_user_permissions(user, oldcadasterdata_instance)
            if not has_permission:
                return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)

            # Serialize and return data
            serializer = self.OldCadasterDetailsOutputSerializer(oldcadasterdata_instance)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except OldCadasterData.DoesNotExist:
            return Response({"detail":"دیتای کاداستر قدیمی با این آیدی یافت نشد"} , status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"{str(e)}")
            return Response(
                {"detail": "خطا در خواندن دیتای قدیمی "}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 
    
    def delete(self, request: Request, oldcadasterid: int) -> Response:
        try:
            user: User = request.user
            oldcadasterdata_instance = OldCadasterData.objects.select_related(
                'province', 'created_by', 'matched_by'
            ).get(pk=oldcadasterid)

            # Check permissions
            has_permission, error_msg = self._check_user_permissions(user, oldcadasterdata_instance)
            if not has_permission:
                return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)

            # Get table name before deletion for cleanup
            table_name = oldcadasterdata_instance.table_name

            table_dropped = drop_table_if_exists(table_name)
            if not table_dropped:
                return Response(
                    {"detail": "خطا در حذف جدول دیتابیس مربوطه"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # Delete the database record
            oldcadasterdata_instance.delete()

            return Response(
                {"detail": "دیتای کاداستر قدیمی با موفقیت حذف شد"}, 
                status=status.HTTP_204_NO_CONTENT
            )    
        except OldCadasterData.DoesNotExist:
            return Response(
                {"detail": "دیتای کاداستر قدیمی با این آیدی یافت نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"Error deleting old cadaster data: {str(e)}")
            return Response(
                {"detail": "خطا در حذف دیتای قدیمی"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CadasterListApiView(APIView):
    """
        - GET (Read from Vector Tile Service Not Handle by Django)
       - POST (Create new Cadaster Instance)     
    """
    pass 

class CadasterDetailsApiView(APIView):
    """
        - GET
        - PUT
        - DELETE
    """
    pass 

class ChangeCadsterStatusApiView(APIView):
    """
        Edit Status of a cadaster instance by user (superuser or user.company.is_moshaver)
    """

    class ChangeCadsterStatusInputSerializer(serializers.Serializer):
        new_status = serializers.IntegerField()
        
        def validate_new_status(self, value):
            valid_statuses = [choice[0] for choice in Cadaster.cadaster_status]
            
            if value not in valid_statuses:
                raise serializers.ValidationError(
                    f"Invalid status. Valid choices are: {valid_statuses}"
                )
            return value

    def put(self , request:Request , cadasterid:int) -> Response:
        try:
            # Check permissions
            if not (request.user.is_superuser or 
                   (hasattr(request.user, 'company') and 
                    getattr(request.user.company, 'is_moshaver', False))):
                return Response(
                    {"error": "شما اجازه انجام این عملیات را ندارید"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get the cadaster instance
            cadaster_instance = Cadaster.objects.get(pk = cadasterid)
            
            # Validate input data
            serializer = self.ChangeCadsterStatusInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            new_status = serializer.validated_data['new_status']
            
            # Check if status is actually changing
            if cadaster_instance.status == new_status:
                return Response(
                    {"message": "وضعیت تغییر داده شده با وضعیت فعلی تفاوتی ندارد"},
                    status=status.HTTP_200_OK
                )
            
            # Update the cadaster instance
            old_status = cadaster_instance.status
            cadaster_instance.status = new_status
            cadaster_instance.change_status_date = timezone.now()
            cadaster_instance.change_status_by = request.user
            cadaster_instance.save()
            
            # # Get status display names for response
            status_dict = dict(Cadaster.cadaster_status)
            
            return Response(
                {
                    "message": "وضعیت با موفقیت تغییر یافت",
                    "cadaster_id": cadasterid,
                    "old_status": {
                        "code": old_status,
                        "name": status_dict.get(old_status, "Unknown")
                    },
                    "new_status": {
                        "code": new_status,
                        "name": status_dict.get(new_status, "Unknown")
                    },
                    "changed_by": request.user.username,
                    "changed_at": cadaster_instance.change_status_date.isoformat()
                },
                status=status.HTTP_200_OK
            )
            
        except Cadaster.DoesNotExist:
            return Response(
                {"error": "کاداستر یافت نشد"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(f"{str(e)}")
            return Response(
                {"error": f"خطا در تغییر وضعیت کاداستر"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
