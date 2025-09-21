from datetime import datetime, timedelta, UTC
from django.db import transaction
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework import exceptions , status
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.permissions import (
    IsAuthenticated,
    IsAdminUser,
)
from common.pagination import CustomPagination
from accounts.models import (
    User,
    Apis,
    Tools,
    Roles,
)
from django.conf import settings
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes


class ApisListApiViews(APIView):
    """
        GET: List of all apis in api model
        POST: Create new api instance
    """
    permission_classes = [IsAdminUser]

    class ApisListOutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Apis
            fields = ['id' , 'method' , 'url' , 'desc']

    class ApisListInputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Apis
            fields = ['method' , 'url' , 'desc']

    def get(self, request: Request) -> Response:
        try:
            all_apis = Apis.objects.all()
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_apis, request)
            serializer = self.ApisListOutputSerializer(paginated_queryset , many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:                      
            print(f"Error in ApisListApiViews: {e}")
            return Response(
                {"detail": "خطا در خواندن لیست دسترسی ها"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def post(self, request: Request) -> Response:
        try:
            serializer = self.ApisListInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            result = serializer.save()
            serialized_result = self.ApisListOutputSerializer(result)
            return Response(serialized_result.data , status=status.HTTP_201_CREATED)
        except Exception as e:                      
            print(f"Error in ApisListApiViews: {e}")
            return Response(
                {"detail": "خطا در ساخت دسترسی جدید"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ApisDetailApiViews(APIView):
    """
        GET: Return an Instance of api model
        PUT: edit an Instance of api model
        DELETE: delete an Instance of api model
    """
    permission_classes = [IsAdminUser]

    class ApisListOutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Apis
            fields = ['id' , 'method' , 'url' , 'desc']

    class ApisListInputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Apis
            fields = ['method' , 'url' , 'desc']

    def get(self, request: Request , apiid:int) -> Response:
        try:
            api_instance = Apis.objects.get(pk = apiid)
            serializer = self.ApisListOutputSerializer(api_instance)
            return Response(serializer.data , status=status.HTTP_200_OK)
        except Apis.DoesNotExist:
            return Response(
                {"detail": "دسترسی با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in ApisListApiViews: {e}")
            return Response(
                {"detail": "خطا در خواندن دسترسی"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def put(self, request: Request , apiid:int) -> Response:
        try:
            api_instance = Apis.objects.get(pk = apiid)
            serializer = self.ApisListInputSerializer(
                api_instance, 
                data=request.data, 
                partial=True  # Allow partial updates
            )
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            updated_api = serializer.save()
            serializer = self.ApisListOutputSerializer(updated_api)
            return Response(serializer.data , status=status.HTTP_200_OK)
        except Apis.DoesNotExist:   
            return Response(
                {"detail": "دسترسی با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in ApisListApiViews: {e}")
            return Response(
                {"detail": "خطا در ویرایش دسترسی"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def delete(self, request: Request , apiid:int) -> Response:
        try:
            api_instance = Apis.objects.get(pk = apiid)
            api_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Apis.DoesNotExist:   
            return Response(
                {"detail": "دسترسی با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in ApisListApiViews: {e}")
            return Response(
                {"detail": "خطا در حذف دسترسی"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ToolsListApiViews(APIView):
    """
        GET: List of all tools in tools model
        POST: Create new tool instance
    """
    permission_classes = [IsAdminUser]

    class ToolsListOutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Tools
            fields = ['id' , 'title' , 'desc']

    class ToolsListInputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Tools
            fields = ['title' , 'desc']

    def get(self, request: Request) -> Response:
        try:
            all_tools = Tools.objects.all()
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_tools, request)
            serializer = self.ToolsListOutputSerializer(paginated_queryset , many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:                      
            print(f"Error in ToolsListApiViews: {e}")
            return Response(
                {"detail": "خطا در خواندن لیست ابزار ها"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def post(self, request: Request) -> Response:
        try:
            serializer = self.ToolsListInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            result = serializer.save()
            serialized_result = self.ToolsListOutputSerializer(result)
            return Response(serialized_result.data , status=status.HTTP_201_CREATED)
        except Exception as e:                      
            print(f"Error in ToolsListApiViews: {e}")
            return Response(
                {"detail": "خطا در ساخت ابزار جدید"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class ToolsDetailApiViews(APIView):
    """
        GET: Return an Instance of tool model
        PUT: edit an Instance of tool model
        DELETE: delete an Instance of tool model
    """
    permission_classes = [IsAdminUser]

    class ToolsListOutputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Tools
            fields = ['id' , 'title' , 'desc']

    class ToolsListInputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Tools
            fields = ['title' , 'desc']

    def get(self, request: Request , toolid:int) -> Response:
        try:
            api_instance = Tools.objects.get(pk = toolid)
            serializer = self.ToolsListOutputSerializer(api_instance)
            return Response(serializer.data , status=status.HTTP_200_OK)
        except Tools.DoesNotExist:
            return Response(
                {"detail": "ابزار با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in ToolsListApiViews: {e}")
            return Response(
                {"detail": "خطا در خواندن دسترسی"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def put(self, request: Request , toolid:int) -> Response:
        try:
            tool_instance = Tools.objects.get(pk = toolid)
            serializer = self.ToolsListInputSerializer(
                tool_instance, 
                data=request.data, 
                partial=True  # Allow partial updates
            )
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            updated_tool = serializer.save()
            updated_tool_serializer = self.ToolsListOutputSerializer(updated_tool)
            return Response(updated_tool_serializer.data , status=status.HTTP_200_OK)
        except Tools.DoesNotExist:   
            return Response(
                {"detail": "ابزار با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in ToolasListApiViews: {e}")
            return Response(
                {"detail": "خطا در ویرایش ابزار"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def delete(self, request: Request , toolid:int) -> Response:
        try:
            tool_instance = Tools.objects.get(pk = toolid)
            tool_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Tools.DoesNotExist:   
            return Response(
                {"detail": "ابزار با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in ToolListApiViews: {e}")
            return Response(
                {"detail": "خطا در حذف ابزار"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class RolesListApiViews(APIView):
    """
        GET: List of all roles in Roles model
        POST: Create new role instance
    """
    permission_classes = [IsAdminUser]

    class RolesListOutputSerializer(serializers.ModelSerializer):
        class RolesListOutputSerializerApis(serializers.ModelSerializer):
            class Meta:
                model = Apis
                fields = ['id' , 'method' , 'url' , 'desc']
        class RolesListOutputSerializerTools(serializers.ModelSerializer):
            class Meta:
                model = Tools
                fields = ['id' , 'title' , 'desc']
        apis = RolesListOutputSerializerApis(many=True)
        tools = RolesListOutputSerializerTools(many=True)
        class Meta:
            model = Roles
            fields = ['id' , 'apis' , 'tools' , 'title' , 'desc']

    class RolesListInputSerializer(serializers.ModelSerializer):
        apis = serializers.PrimaryKeyRelatedField(
           queryset=Apis.objects.all(),
            many=True
        )
        tools = serializers.PrimaryKeyRelatedField(
            queryset=Tools.objects.all(),
            many=True
        )
        class Meta:
            model = Roles
            fields = ['apis' , 'tools' , 'title' , 'desc']

    def get(self, request: Request) -> Response:
        try:
            all_roles = Roles.objects.all()
            paginator = CustomPagination()
            paginated_queryset = paginator.paginate_queryset(all_roles, request)
            serializer = self.RolesListOutputSerializer(paginated_queryset , many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:                      
            print(f"Error in RolesListApiViews: {e}")
            return Response(
                {"detail": "خطا در خواندن لیست نقش ها"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def post(self, request: Request) -> Response:
        try:
            serializer = self.RolesListInputSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            result = serializer.save()
            serialized_result = self.RolesListOutputSerializer(result)
            return Response(serialized_result.data , status=status.HTTP_201_CREATED)
        except Exception as e:                      
            print(f"Error in ًRolesListApiViews: {e}")
            return Response(
                {"detail": "خطا در ساخت نقش جدید"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class RolesDetailApiViews(APIView):
    """
        GET: Return an Instance of roles model
        PUT: edit an Instance of roles model
        DELETE: delete an Instance of roles model
    """
    permission_classes = [IsAdminUser]
    class RolesDetailOutputSerializer(serializers.ModelSerializer):
        class RolesDetailOutputSerializerApis(serializers.ModelSerializer):
            class Meta:
                model = Apis
                fields = ['id' , 'method' , 'url' , 'desc']
        class RolesDetailOutputSerializerTools(serializers.ModelSerializer):
            class Meta:
                model = Tools
                fields = ['id' , 'title' , 'desc']
        apis = RolesDetailOutputSerializerApis(many=True)
        tools = RolesDetailOutputSerializerTools(many=True)
        class Meta:
            model = Roles
            fields = ['id' , 'apis' , 'tools' , 'title' , 'desc']

    class RolesDetailInputSerializer(serializers.ModelSerializer):
        apis = serializers.PrimaryKeyRelatedField(
           queryset=Apis.objects.all(),
            many=True
        )
        tools = serializers.PrimaryKeyRelatedField(
            queryset=Tools.objects.all(),
            many=True
        )
        class Meta:
            model = Roles
            fields = ['apis' , 'tools' , 'title' , 'desc']

    def get(self, request: Request , roleid:int) -> Response:
        try:
            role_instance = Roles.objects.get(pk = roleid)
            serializer = self.RolesDetailOutputSerializer(role_instance)
            return Response(serializer.data , status=status.HTTP_200_OK)
        except Roles.DoesNotExist:
            return Response(
                {"detail": "نقش با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in RolesListApiViews: {e}")
            return Response(
                {"detail": "خطا در خواندن نقش"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    def put(self, request: Request , roleid:int) -> Response:
        try:
            role_instance = Roles.objects.get(pk = roleid)
            serializer = self.RolesDetailInputSerializer(
                role_instance, 
                data=request.data, 
                partial=True  # Allow partial updates
            )
            if not serializer.is_valid():
                return Response({"details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            updated_role = serializer.save()
            updated_role_serializer = self.RolesDetailOutputSerializer(updated_role)
            return Response(updated_role_serializer.data , status=status.HTTP_200_OK)
        except Roles.DoesNotExist:   
            return Response(
                {"detail": "نقش با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in RolesListApiViews: {e}")
            return Response(
                {"detail": "خطا در ویرایش نقش"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    def delete(self, request: Request , roleid:int) -> Response:
        try:
            role_instance = Roles.objects.get(pk = roleid)
            role_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Roles.DoesNotExist:   
            return Response(
                {"detail": "نقش با این آیدی پیدا نشد"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:                      
            print(f"Error in RolesListApiViews: {e}")
            return Response(
                {"detail": "خطا در حذف نقش"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )