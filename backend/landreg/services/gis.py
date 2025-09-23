import zipfile
import tempfile
import os
import shutil
from typing import Tuple, Dict, Any, Optional , List  , TypedDict
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
import geopandas as gpd
import pandas as pd
from geopandas import GeoDataFrame
from django.contrib.gis.geos import MultiPolygon, Polygon
from shapely.geometry import MultiPolygon as ShapelyMultiPolygon, Polygon as ShapelyPolygon

from django.core.files.uploadedfile import InMemoryUploadedFile


from common.services.gis_services import (
    validate_geodataframe,
    get_geometry_type
)


class PekakResult(TypedDict):
    title: str
    number: str
    border: Polygon

def process_pelak_border(
        zipfile_obj:InMemoryUploadedFile,
        ) -> Tuple[bool, List[PekakResult], str]:
    """

    """
    temp_dir = None
    try:
        # Reset file pointer to beginning
        zipfile_obj.seek(0)
        # Create temporary directory for extraction
        temp_dir = tempfile.mkdtemp()
        # Extract ZIP file contents
        with zipfile.ZipFile(zipfile_obj, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        # Find shapefile (.shp file)
        shp_file = None
        extracted_files = os.listdir(temp_dir)
        for file in extracted_files:
            if file.lower().endswith('.shp'):
                shp_file = os.path.join(temp_dir, file)
                break
        if not shp_file:
            return False, [], 'فایلی با فرمت .shp در زیپ فایل یافت نشد'
        # Check for required shapefile components
        base_name = os.path.splitext(shp_file)[0]
        required_extensions = ['.shp', '.shx', '.dbf']
        missing_files = []
        for ext in required_extensions:
            if not os.path.exists(base_name + ext):
                missing_files.append(ext)
        if missing_files:
            return False, [], f'این فایل ها در زیپ فایل یافت نشد: {missing_files}'
        
        # Read shapefile into GeoDataFrame
        try:
            gdf = gpd.read_file(shp_file)
        except Exception as e:
            return False, [], f'خطا در خواندن شیپ فایل: {str(e)}'
        
        # Validate GeoDataFrame using common service
        is_valid, validation_error = validate_geodataframe(gdf)
        if not is_valid:
           return False, [], f'خطا در اعتبارسنجی شیپ فایل: {validation_error}'
        
        # Check for required columns
        if 'title' not in gdf.columns:
            return False, [], 'ستون title در شیپ فایل یافت نشد'
        
        if 'number' not in gdf.columns:
            return False, [], 'ستون number در شیپ فایل یافت نشد'
        
        # Check geometry type using common service
        try:
            geometry_type = get_geometry_type(gdf)
            if geometry_type != 'polygon':
                return False, [], f'نوع هندسه پشتیبانی نمی‌شود. فقط پولیگون مجاز است، دریافت شده: {geometry_type}'
        except Exception as e:
            return False, [], f'خطا در تشخیص نوع هندسه: {str(e)}'
        
        # Ensure the GeoDataFrame is in WGS84 (EPSG:4326)
        if gdf.crs is None:
            return False, [], 'سیستم مختصات شیپ فایل مشخص نیست'
        
        if gdf.crs.to_epsg() != 4326:
            try:
                gdf = gdf.to_crs(epsg=4326)
            except Exception as e:
                return False, [], f'خطا در تبدیل سیستم مختصات: {str(e)}'
            
        # Extract all polygons from the GeoDataFrame
        result_data : List[PekakResult] = []
        already_added_number : List[str] = []


        for idx, row in gdf.iterrows():
            geometry = row.geometry
            title = row.get('title' , 'بدون نام')
            number = row.get('number')
            
            if geometry is None or geometry.is_empty:
                continue

            # Check if title and scale have values
            # if pd.isna(title) or title == '' or title is None:
            #     return False , [] , f"مقدار ستون title برای ردیف {idx+1} خالی میباشد"
                
            if pd.isna(number) or number == '' or number is None:
                return False , [] , f"مقدار ستون number برای ردیف {idx+1} خالی میباشد"
            
            #title unique validate
            if title in already_added_number:
                return False , [] , f"مقدار number برای عنوان {number} یکتا نیست"
            else:
                already_added_number.append(title)
                            
                
            # Handle different geometry types
            if isinstance(geometry, ShapelyPolygon):
                # Single polygon - convert to Django Polygon
                try:
                    # Convert coordinates to list of tuples for Django Polygon
                    exterior_coords = list(geometry.exterior.coords)
                    django_polygon = Polygon(exterior_coords)
                    result_data.append({
                        'border': django_polygon,
                        'title': title,
                        'number': number
                    })
                except Exception as e:
                    print(f"Error converting polygon at index {idx+1}: {e}")
                    continue
                    
            elif isinstance(geometry, ShapelyMultiPolygon):
                return False , [] , "اجازه ورود multipolygon برای محدوده پلاک وجود ندارد لطفا آن را به polygon تبدیل کنید"
            else:
                # This should not happen after geometry type validation, but keep as safety
                print(f"Unexpected geometry type at index {idx}: {type(geometry)}")
                continue

        if not result_data:
            return False, [], 'هیچ پولیگون معتبری در شیپ فایل یافت نشد'

        return True, result_data, 'عملیات با موفقیت انجام شد'
        
        
    except zipfile.BadZipFile:
        return False, [], 'زیپ فایل نامعتبر می‌باشد'
    except Exception as e:
       print(e)
       return False, [], f'خطای غیر منتظره در پردازش زیپ فایل'
    
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temporary directory: {e}")