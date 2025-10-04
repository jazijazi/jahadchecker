import zipfile
from django.utils import timezone
from typing import cast, Dict, Any , List
from django.core.validators import FileExtensionValidator
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import serializers
from rest_framework.permissions import AllowAny , IsAdminUser , IsAuthenticated
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
    process_shp_file,
    drop_table_if_exists,

    get_layersnames_from_zipped_geodatabase,
    save_gdbzipfile_into_tempdir_with_uuid,
) 
from landreg.services.convert_service import (
    validate_cadaster_column_mapping,
    get_status_code,
    import_cadaster_data,
)
from geoserverapp.services.geoserver_service import GeoServerService
from landreg.exceptions import (
    TableNotFoundError,
    GeoDatabaseValidationError,
    CadasterImportError
)
from django.conf import settings
from landreg.models.flag import Flag
from landreg.models.cadaster import Cadaster , OldCadasterData
from common.models import Company , Province
from accounts.models import User
from landreg.services.database_service import get_table_columns 
from django.core.files.uploadedfile import InMemoryUploadedFile


class UploadOldCadasterFromShapefileApiView(APIView):
    """
        1. upload oldcadaster data as a Shapefile !
        2. save the shapefile in OldCadasterData
        *** only user.issuperuser and user.company.is_nazer can use this api
    """
    
    class UploadOldCadasterFromShapefileInputSerializer(serializers.Serializer):
        file = serializers.FileField(
            required=False,
            allow_null=True,
            validators=[
                FileExtensionValidator(
                    allowed_extensions=['zip'],
                    message="فایل محدوده حتما باید با فرمت zip باشد"
                )
            ]
        )
        province_selected_id = serializers.IntegerField(
            required=False,
            allow_null=True,  # Allow null for non-superusers
        )

        def validate_province_selected_id(self, value):
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
 
    class UploadOldCadasterFromShapefileOutputSerializer(serializers.ModelSerializer):
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
        
    def _cleanup(self , tablenames:List[str]):
        if len(tablenames)>0:
            for t_name in tablenames:
                drop_table_if_exists(t_name)
                if OldCadasterData.objects.filter(table_name=t_name).exists():
                    OldCadasterData.objects.filter(table_name=t_name).first().delete()

    def post(self , request:Request) -> Response:
        created_oldcadasterdata : List[OldCadasterData] = []
        published_tablename : List[str] = []

        try:
            user:User = request.user
            
            has_permission, error_msg = self._check_user_permissions(user)
            if not has_permission:
                return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)
            
            input_serializer = self.UploadOldCadasterFromShapefileInputSerializer(data=request.data)
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
            
            
            from landreg.services.gis import ProcessResult
            result:List[ProcessResult] = process_shp_file(
                shpzipfile=validated_data['file']
            )

            for res in result:
                oldcadasterdata_new_instance = OldCadasterData.objects.create(
                    table_name = res["table_name"],
                    created_by = user,
                    province = province_instance,
                )
                created_oldcadasterdata.append(oldcadasterdata_new_instance)

            geoserver_service = GeoServerService()
            if len(created_oldcadasterdata) > 0:
                for c_old in created_oldcadasterdata:
                    pub_res = geoserver_service.pulish_layer(
                        workspace=settings.GEOSERVER['DEFAULT_WORKSPACE'],
                        store_name=settings.GEOSERVER['DEFAULT_STORE'],
                        pg_table=c_old.table_name,
                        title=c_old.table_name,
                    )
                    if pub_res.get("status",400) == 201:
                        published_tablename.append(c_old.table_name)


            output_serializer = self.UploadOldCadasterFromShapefileOutputSerializer(created_oldcadasterdata,many=True)
            return Response(output_serializer.data , status=status.HTTP_201_CREATED)
            
        except GeoDatabaseValidationError as gdderr:
            self._cleanup(tablenames = published_tablename)
            return Response({"detail": f"{str(gdderr)}"}, status=status.HTTP_400_BAD_REQUEST)
        except FileNotFoundError as ferr:
            self._cleanup(tablenames = published_tablename)
            return Response({"detail": f"{str(ferr)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            self._cleanup(tablenames = published_tablename)
            print(f"Error creating cadaster via shpfile: {str(e)}")
            return Response(
                {"detail": "خطا در بارگذاری دیتای قدیمی "}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 


class UploadOldCadasterFromGdbApiView(APIView):
    """
        1. upload oldcadaster data as a geodatabase !
        2. get layers from geodatabase and save them to postgres as a new table for each layer
        3. save the tablename (and other data) in OldCadasterData
        *** only user.issuperuser and user.company.is_nazer can use this api
    """

    class UploadOldCadasterFromGdbInputSerializer(serializers.Serializer):
        uuid = serializers.CharField(required=True,
            help_text="uuid is file path uuid",
            error_messages={
                'required': "این فیلد اجباری است",
                'blank': "این فیلد نمیتواند خالی باشد.",
                'null': "این فیلد نمیتواند null باشد."
            }
        )
        selectedlayers = serializers.ListField(
            child=serializers.CharField(),
            required=True,
            help_text="لیستی از لایه های انتخاب شده برای بارگذاری",
            error_messages={
                'required': "این فیلد اجباری است",
                'blank': "این فیلد نمیتواند خالی باشد.",
                'null': "این فیلد نمیتواند null باشد."
            }
        )
        
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
            
    class UploadOldCadasterFromGdbOutputSerializer(serializers.ModelSerializer):
        
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
            
    def _cleanup(self , tablenames:List[str]):
        if len(tablenames)>0:
            for t_name in tablenames:
                drop_table_if_exists(t_name)
                if OldCadasterData.objects.filter(table_name=t_name).exists():
                    OldCadasterData.objects.filter(table_name=t_name).first().delete()
        
    def post(self, request:Request) -> Response:
        created_oldcadasterdata : List[OldCadasterData] = []
        published_tablename : List[str] = []
        try:
            user:User = request.user
            
            has_permission, error_msg = self._check_user_permissions(user)
            if not has_permission:
                return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)
            
            input_serializer = self.UploadOldCadasterFromGdbInputSerializer(data=request.data)
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
            
            
            from landreg.services.gis import ProcessResult
            result:List[ProcessResult] = process_gdb_file(
                geodb_uuid = input_serializer.validated_data.get('uuid'),
                selectedlayers = input_serializer.validated_data.get('selectedlayers')
            )
            

            for res in result:
                oldcadasterdata_new_instance = OldCadasterData.objects.create(
                    table_name = res["table_name"],
                    created_by = user,
                    province = province_instance,
                )
                created_oldcadasterdata.append(oldcadasterdata_new_instance)

            geoserver_service = GeoServerService()
            if len(created_oldcadasterdata) > 0:
                for c_old in created_oldcadasterdata:
                    pub_res = geoserver_service.pulish_layer(
                        workspace=settings.GEOSERVER['DEFAULT_WORKSPACE'],
                        store_name=settings.GEOSERVER['DEFAULT_STORE'],
                        pg_table=c_old.table_name,
                        title=c_old.table_name,
                    )
                    if pub_res.get("status",400) == 201:
                        published_tablename.append(c_old.table_name)

            output_serializer = self.UploadOldCadasterFromGdbOutputSerializer(created_oldcadasterdata,many=True)
            return Response(output_serializer.data , status=status.HTTP_201_CREATED)

        except GeoDatabaseValidationError as gdderr:
            return Response({"detail": f"{str(gdderr)}"}, status=status.HTTP_400_BAD_REQUEST)

        except FileNotFoundError as ferr:
            self._cleanup(tablenames = published_tablename)
            return Response({"detail": f"{str(ferr)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            self._cleanup(tablenames = published_tablename)
            print(f"Error creating cadaster via Geodatabase: {str(e)}")
            return Response(
                {"detail": "خطا در بارگذاری دیتای قدیمی "}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 
        
class OldCadasterListApiView(APIView):
    """
        Object level permission
        - superuser and supernazer get all
        - nazer and mohaver get only thoes in same proviance
    """
    class OldCadasterListOutputSerializer(serializers.ModelSerializer):
        class OldCadasterListOutputSerializerUser(serializers.ModelSerializer):
            class Meta:
                model = User
                fields = ['id','username','first_name_fa','last_name_fa']
        class OldCadasterListOutputSerializerProvince(serializers.ModelSerializer):
            class Meta:
                model = Province
                fields = ['id','name_fa']

        matched_by = OldCadasterListOutputSerializerUser()
        province = OldCadasterListOutputSerializerProvince()
        class Meta:
            model = OldCadasterData
            fields = ['table_name','created_by','status','matched_by','matched_at','province']

    def _check_user_permissions(self, user: User) -> tuple[bool, str]:
        """user must be superuser or moshaver or nazer"""
        if user.is_superuser:
            return True, ""
        
        if not user.company:
            return False, "کاربر بدون شرکت است"
        
        if not (user.company.is_nazer or user.company.is_moshaver):
            return False, "شما اجازه خواندن کاداستر قدیمی را ندارید"
        
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
        
    def get(self , request:Request) -> Response:
        # Check permissions first
        has_permission, error_msg = self._check_user_permissions(request.user)
        if not has_permission:
            return Response({"detail": error_msg}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = request.user
            province_id_param = request.query_params.get('province_id',None)
            province_instance , message = self._get_province_for_user(user=user,province_id=province_id_param)
            if not province_instance:
                return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN) 
            all_oldcadaster_instance = OldCadasterData.objects.filter(province=province_instance)
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_oldcadaster_instance, request)
            serializer = self.OldCadasterListOutputSerializer(paginated_queryset,many=True,context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            print(f"Error creating pelak: {str(e)}")
            return Response(
                {"detail": "خطا خواندن دیتای کاداستر قدیمی "}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    class CadasterDetailsInputSerializer(serializers.ModelSerializer):

        class Meta:
            model = Cadaster
            fields = ['uniquecode','jaam_code','plak_name',
                      'plak_asli','plak_farei','bakhsh_sabti',
                      'nahiye_sabti','area','owner_name','owner_lastname',
                      'fathername','national_code','mobile','ownership_kinde',
                      'consulate_name','nezarat_type',
                      'project_name','land_use','irrigation_type',
                    ]
    
    class CadasterDetailsOuputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Cadaster
            fields = ['id','uniquecode','jaam_code','plak_name',
                      'plak_asli','plak_farei','bakhsh_sabti',
                      'nahiye_sabti','area','owner_name','owner_lastname',
                      'fathername','national_code','mobile','ownership_kinde',
                      'consulate_name','nezarat_type',
                      'project_name','land_use','irrigation_type',
                    ]
            
    def get(self , request:Request , cadasterid:int) -> Response:
        try:
            cadster_instance = Cadaster.objects.get(pk=cadasterid)
            serializer = self.CadasterDetailsOuputSerializer(cadster_instance)
            return Response(serializer.data , status=status.HTTP_200_OK)
        except Cadaster.DoesNotExist:
            return Response({"detail": f"کاداستر با این آیدی یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"detail": f"خطا در خواندن کاداستری با این آیدی"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request: Request , cadasterid:int) -> Response:
        try:
            cadster_instance = Cadaster.objects.get(pk=cadasterid)
            serializer = self.CadasterDetailsInputSerializer(
                cadster_instance, 
                data=request.data, 
                partial=True  # Allow partial updates
            )
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            cadster_instance = serializer.save()
            serializer = self.CadasterDetailsOuputSerializer(cadster_instance)
            return Response(serializer.data , status=status.HTTP_200_OK)
        except Cadaster.DoesNotExist:
            return Response({"detail": f"کاداستر با این آیدی یافت نشد"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"detail": f"خطا در ویرایش کاداستری با این آیدی"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




class GetListLayersFromGeodbFile(APIView):
    """
    API to get all layers from zipped GeoDatabase 
    """
    permission_classes = [IsAuthenticated]

    class GetListLayersFromGeodbFileInputSerializer(serializers.Serializer):
        gdbzipfile = serializers.FileField(required=True,
            help_text="ZIP file containing the gdb file",
            error_messages={
                'required': "این فیلد اجباری است",
                'blank': "این فیلد نمیتواند خالی باشد.",
                'null': "این فیلد نمیتواند null باشد."
            })
          
        def validate_gdbzipfile(self,value):
            if not zipfile.is_zipfile(value):
                raise serializers.ValidationError("فایل باید از نوع ZIP باشد.")
            
    def post(self, request:Request) -> Response:
        """
        get a zip file in requst files 
        get gdb from fille after unzip the file
        get all layers from zipped file and return it in Response 
        """

        input_serializer = self.GetListLayersFromGeodbFileInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        gdbzipfile = request.FILES['gdbzipfile']

        try:
            all_layer_list = get_layersnames_from_zipped_geodatabase(gdb_zip_file=gdbzipfile)

            dir_uuid = save_gdbzipfile_into_tempdir_with_uuid(gdb_zip_file=gdbzipfile)

            return Response({
                "layers": all_layer_list,
                "uuid": dir_uuid,
            }, status=status.HTTP_200_OK)
        
        except GeoDatabaseValidationError as gdderr:
            return Response({"detail": f"{str(gdderr)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"{str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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


class TableColumnNamesAPIView(APIView):
    permission_classes = [IsAuthenticated] #TODO : Dynamic & only mohaver and superuser allow to this view
    """
    Get columns and types of a PostGIS table.
    Expects JSON body: { "table_name": "your_table_name" }
    """
    def post(self, request):
        table_name = request.data.get("table_name")
        schema = request.data.get("schema")  # Optional schema parameter
        
        if not table_name:
            return Response(
                {"error": "table_name is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            columns = get_table_columns(table_name, schema)
            return Response({
                "table_name": table_name,
                "schema": schema or "public",
                "columns": columns,
                "column_count": len(columns)
            })
            
        except ValueError as e:
            return Response(
                {"error": f"Invalid input: {e}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except TableNotFoundError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )
                        
        except Exception as e:
            return Response(
                {"error": "An unexpected error occurred"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CadasterColumnMappingValidateAPIView(APIView):
    permission_classes = [IsAuthenticated] #TODO : Dynamic & only mohaver and superuser allow to this view
    
    def post(self, request):
        source_table_name = request.data.get("source_table_name")
        source_table_schema = request.data.get("source_table_schema", "public")
        matched_fields = request.data.get("matched_fields", [])
        
        # Validation
        if not source_table_name:
            return Response(
                {"error": "نام جدول مبدا (source_table_name) الزامی است"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(matched_fields, list):
            return Response(
                {"error": "فیلد matched_fields باید یک لیست باشد"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(matched_fields) == 0:
            return Response(
                {"error": "حداقل یک نگاشت ستون مورد نیاز است"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validate the mapping
            validation_result = validate_cadaster_column_mapping(
                source_table_name, 
                source_table_schema, 
                matched_fields
            )
            
            # Determine response status based on validation results
            status_code = get_status_code(validation_result['mapping_summary'])
            validation_result['status_code'] = status_code
            
            if status_code == -1:
                response_status = status.HTTP_400_BAD_REQUEST
                validation_result['status'] = 'validation_failed'
                validation_result['message'] = 'برخی از نگاشت‌های ستون نامعتبر هستند'
            elif status_code == 0:
                response_status = status.HTTP_200_OK
                validation_result['status'] = 'validation_passed_with_warnings'
                validation_result['message'] = 'نگاشت‌های ستون معتبر هستند اما دارای هشدار می‌باشند'
            else:  # status_code == 1
                response_status = status.HTTP_200_OK
                validation_result['status'] = 'validation_passed'
                validation_result['message'] = 'همه نگاشت‌های ستون معتبر هستند'
            
            return Response(validation_result, status=response_status)
            
        except ValueError as e:
            return Response(
                {"error": f"ورودی نامعتبر: {e}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except TableNotFoundError as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            return Response(
                {"error": "خطای غیرمنتظره‌ای رخ داده است"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class CadasterImportAPIView(APIView):
    permission_classes = [IsAuthenticated] #TODO : Dynamic & only mohaver and superuser allow to this view
    """
    Import data from source table to Cadaster model.
    """
    
    def post(self, request):
        source_table_name = request.data.get("source_table_name")
        source_table_schema = request.data.get("source_table_schema", "public")
        matched_fields = request.data.get("matched_fields", [])
        
        # Validation
        if not source_table_name:
            return Response(
                {"error": "نام جدول مبدا (source_table_name) الزامی است"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not isinstance(matched_fields, list) or len(matched_fields) == 0:
            return Response(
                {"error": "حداقل یک نگاشت ستون مورد نیاز است"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            old_cadaster_instance = OldCadasterData.objects.get(table_name=source_table_name)

            # First validate the mapping
            validation_result = validate_cadaster_column_mapping(
                source_table_name, 
                source_table_schema, 
                matched_fields
            )
            
            status_code = get_status_code(validation_result['mapping_summary'])
            
            # Only proceed if validation passed (with or without warnings)
            if status_code == -1:
                return Response(
                    {
                        "error": "نگاشت‌های ستون نامعتبر هستند. لطفاً ابتدا نگاشت‌ها را اصلاح کنید",
                        "validation_errors": validation_result['invalid_mappings']
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Perform import
            import_result = import_cadaster_data(
                source_table_name,
                source_table_schema,
                matched_fields,
            )
            
            # Check if import was successful
            if not import_result['success']:
                return Response(
                    {
                        "error": import_result.get('message', 'عملیات import ناموفق بود'),
                        "import_summary": import_result
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            #change oldcadaster record
            old_cadaster_instance.status = OldCadasterData.Status.MATCHED
            old_cadaster_instance.matched_by = request.user
            old_cadaster_instance.matched_at = timezone.now()
            old_cadaster_instance.save()
            
            response_data = {
                "message": "عملیات import با موفقیت انجام شد",
                "import_summary": import_result,
                "validation_warnings": validation_result.get('general_warnings', []) if status_code == 0 else []
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except CadasterImportError as e:
            import traceback
            print(traceback.format_exc())

            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except TableNotFoundError as e:
            import traceback
            print(traceback.format_exc())
            
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        except Exception as e:
            # Log the full error for debugging
            import traceback
            print(traceback.format_exc())
            
            return Response(
                {"error": f"خطای غیرمنتظره: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
