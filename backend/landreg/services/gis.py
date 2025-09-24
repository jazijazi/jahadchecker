import zipfile
import tempfile
import os
import re
import shutil
import uuid
from typing import Tuple, Dict, Any, Optional , List  , TypedDict
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
import geopandas as gpd
import pandas as pd
import fiona
from geopandas import GeoDataFrame
from django.contrib.gis.geos import MultiPolygon, Polygon
from shapely.geometry import MultiPolygon as ShapelyMultiPolygon, Polygon as ShapelyPolygon

from django.core.files.uploadedfile import InMemoryUploadedFile
from landreg.exceptions import (
    GeoDatabaseValidationError ,
    SqlAlchemyEnginError,
    GeoFrameValidationError,
)

from common.services.gis_services import (
    validate_geodataframe,
    get_geometry_type
)

from landreg.services.tablename_service import (
    validate_word_as_database_tablename,
    add_unique_suffix_to_layername
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





from sqlalchemy import create_engine , Engine , text
from urllib.parse import quote_plus
from django.conf import settings

def create_new_database_engine() -> Engine:
    """
    Create a database engine with sqlalchemy and database values from setting if django
    """
    db_settings = settings.DATABASES['default']

    user = quote_plus(db_settings['USER'])
    password = quote_plus(db_settings['PASSWORD'])
    host = db_settings['HOST']
    port = db_settings['PORT']
    db_name = db_settings['NAME']

    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

    try:
        engine = create_engine(db_url)
    except Exception as e:
        raise SqlAlchemyEnginError(f"Failed to create engine: {e}")

    return engine

class ProcessResult(TypedDict):
    # Required keys
    table_name: str
    type_geo: str
    feature_count: int

def drop_table_if_exists(table_name: str) -> bool:
    """
    Safely drop a table from the database if it exists.
    
    Args:
        table_name: Name of the table to drop.
    
    Returns:
        bool: True if drop command executed without error, False otherwise.
    """
    try:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
            raise ValueError(f"Invalid table name: {table_name}")

        engine = create_new_database_engine()

        with engine.begin() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))

        print(f"Table '{table_name}' dropped successfully (if it existed).")
        return True

    except Exception as e:
        print("Error dropping table:", e)
        return False
    
def process_geodataframe_into_postgisdb(table_name:str,gdf:GeoDataFrame)->ProcessResult:
    """
    Insert a GeoDataFrame into postgis database
    """

    # Create database engine
    engine = create_new_database_engine()

    # Validate shapefile content
    is_valid, error_message = validate_geodataframe(gdf)
    if not is_valid:
        raise GeoFrameValidationError(f"{error_message} for {table_name}")
    
    # Ensure CRS is set to WGS84 (EPSG:4326)
    if gdf.crs is None:
        gdf.set_crs(epsg=4326, inplace=True)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Get geometry type
    type_geo = get_geometry_type(gdf)
    
    try:
        # Write to PostGIS
        gdf.to_postgis(
            name=table_name, 
            con=engine, 
            if_exists='replace', 
            index=False
        )
    except Exception as e:
        raise Exception(f"Error writing to database: {e}")

    res : ProcessResult = {
        "table_name":table_name,
        "type_geo": type_geo,
        "feature_count": len(gdf),
    }
    return res

def process_gdb_file(
    gdbzipfile: InMemoryUploadedFile
) -> Any:
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdirname:
        zip_path = os.path.join(tmpdirname, f"gdbzipfile_{uuid.uuid4().hex[:8]}.zip")

        # Save the uploaded file to the temp directory
        with open(zip_path, 'wb+') as f:
            for chunk in gdbzipfile.chunks():
                f.write(chunk)

        result: List[ProcessResult] = []
        created_tables: List[str] = []
        
        try:
            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdirname)
        except zipfile.BadZipFile:
            raise GeoDatabaseValidationError("فایل زیپ شده ورودی معتبر نمیباشد")

        # Find geodatabase file in the extracted directory
        gdb_files = [f for f in os.listdir(tmpdirname) if f.endswith('.gdb')]
        if not gdb_files:
            raise GeoDatabaseValidationError("فایلی با پسوند .gdb در فایل زیپ شده ورودی یافت نشد")

        gdb_path = os.path.join(tmpdirname, gdb_files[0])

        try:
            # Get layer names from the geodatabase
            layer_names = fiona.listlayers(gdb_path)
            
            # validate each layer
            for lyrnm in layer_names:
                # validate layer name
                res , message = validate_word_as_database_tablename(word=lyrnm)
                if not res:
                    raise Exception(f"لایه {lyrnm} : {message}")
                # Get gdf for this layer
                gdf = gpd.read_file(gdb_path, layer=lyrnm)
                # validate this gdf
                res_validate , res_message = validate_geodataframe(gdf=gdf)
                if not res_validate:
                    raise Exception(f"لایه {lyrnm} خطای {res_message} دارد")

            #After sure all gdf`s validate and clean
            for lyrnm in layer_names:
                gdf = gpd.read_file(gdb_path, layer=lyrnm)
                
                lyrnm_with_suffix = add_unique_suffix_to_layername(originallayername=lyrnm)
                
                res:ProcessResult = process_geodataframe_into_postgisdb(
                    table_name=lyrnm_with_suffix,
                    gdf=gdf
                )

                # Track successfully created table
                created_tables.append(lyrnm_with_suffix)
                result.append(res)


            return result
            
        except Exception as e:
            print(f"Error occurred: {e}")
            print(f"Rolling back {len(created_tables)} created tables...")
            
            for table_name in created_tables:
                try:
                    drop_table_if_exists(table_name)
                    print(f"Dropped table: {table_name}")
                except Exception as drop_error:
                    print(f"Failed to drop table {table_name}: {drop_error}")

            raise GeoDatabaseValidationError(f"خطا در خواندن ژیودیتابیس")
        
