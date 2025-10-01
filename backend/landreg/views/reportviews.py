from typing import cast, Dict, Any
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework import serializers
from common.pagination import CustomPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.db.models import Count, Case, When, IntegerField
from django.conf import settings
from landreg.models.cadaster import Cadaster
from landreg.models.flag import Flag
from common.models import Company , Province
from accounts.models import User



class CadaterStatusByProvince(APIView):
    #permission is dynamic
    """
        - Get a id of province from url 
        - Get the proviance
        - Intersect the province.border with all Cadaster.border instances
        - Return status count of all founded Cadasters
    """

    def post(self, request: Request, provinceid) -> Response:
        try:
            # Check cache first (cache for 5 minutes)
            cache_key = f'report_cadaster_by_province_status_{provinceid}'
            
            if not settings.DEBUG: # in debug mode do not use cache
                cached_result = cache.get(cache_key)
                if cached_result:
                    return Response(cached_result, status=status.HTTP_200_OK)

            # Use only() to fetch only required fields
            province_instance = Province.objects.only('id', 'name_fa', 'border').get(pk=provinceid)

            # Single query with conditional aggregation for all statuses
            status_aggregation = {
                f'status_{code}': Count(
                    Case(When(status=code, then=1), output_field=IntegerField())
                )
                for code, _ in Cadaster.cadaster_status
            }

            # Execute single aggregation query
            counts = Cadaster.objects.filter(
                border__intersects=province_instance.border
            ).aggregate(
                total=Count('id'),
                **status_aggregation
            )

            # Build response
            result = {
                'province_id': provinceid,
                'province_name': province_instance.name_fa,
                'total_cadasters': counts['total'],
                'status_breakdown': [
                    {
                        'status_code': status_code,
                        'status_label': status_label,
                        'count': counts[f'status_{status_code}']
                    }
                    for status_code, status_label in Cadaster.cadaster_status
                ]
            }

            if not settings.DEBUG:# in Debug mode do not Cache the result
                cache.set(cache_key, result, 300)  # cache fot 5 minutes

            return Response(result, status=status.HTTP_200_OK)
        
        except Province.DoesNotExist:
            return Response({"detail":"استانی با این آیدی یافت نشد"} , status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"detail": "خطا در آمار وضعیت کاداسترها بر اساس استان"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class FlagStatusByProvince(APIView):
    #permission is dynamic
    """
        - Get a id of province from url 
        - Get the proviance
        - Intersect the province.border with all flag.border (its point) instances
        - Return status count of all founded Cadasters
    """

    def post(self, request: Request, provinceid) -> Response:
        try:
            # Check cache first (cache for 5 minutes)
            cache_key = f'report_flag_by_province_status_{provinceid}'
            
            if not settings.DEBUG: # in debug mode do not use cache
                cached_result = cache.get(cache_key)
                if cached_result:
                    return Response(cached_result, status=status.HTTP_200_OK)

            # Use only() to fetch only required fields
            province_instance = Province.objects.only('id', 'name_fa', 'border').get(pk=provinceid)

            # Single query with conditional aggregation for all statuses
            status_aggregation = {
                f'status_{code}': Count(
                    Case(When(status=code, then=1), output_field=IntegerField())
                )
                for code, _ in Flag.FLAG_STATUS_CHOICES
            }

            # Execute single aggregation query
            counts = Flag.objects.filter(
                border__intersects=province_instance.border
            ).aggregate(
                total=Count('id'),
                **status_aggregation
            )

            # Build response
            result = {
                'province_id': provinceid,
                'province_name': province_instance.name_fa,
                'total_flags': counts['total'],
                'status_breakdown': [
                    {
                        'status_code': status_code,
                        'status_label': status_label,
                        'count': counts[f'status_{status_code}']
                    }
                    for status_code, status_label in Flag.FLAG_STATUS_CHOICES
                ]
            }

            if not settings.DEBUG:# in Debug mode do not Cache the result
                cache.set(cache_key, result, 300)  # cache fot 5 minutes

            return Response(result, status=status.HTTP_200_OK)
        
        except Province.DoesNotExist:
            return Response({"detail":"استانی با این آیدی یافت نشد"} , status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"detail":  "خطا در آمار وضعیت فلگ ها بر اساس استان"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )