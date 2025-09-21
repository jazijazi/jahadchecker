import os
import zipfile
import tempfile
from urllib.parse import quote_plus
from uuid import uuid4
from typing import List , Tuple , Dict , Any , TypedDict
from django.core.files.uploadedfile import InMemoryUploadedFile

from common.exceptions import (
    GeoFrameValidationError,
)

import fiona
import geopandas as gpd
from geopandas import GeoDataFrame
from django.conf import settings
from shapely.geometry import MultiPolygon, Polygon

# from layercore.services.tablename_service import add_unique_suffix_to_tablename

# from layercore.utils import (
#     GeoFrameValidationError,
#     GeoServerError,
#     ShapefileValidationError,
#     SldValidationError,
#     GeoDatabaseValidationError,
# )

def validate_geodataframe(gdf : GeoDataFrame) -> Tuple[bool, str]:
    """
    Validate the GeoDataFrame data before processing
    
    Args:
        gdf: GeoDataFrame with the shapefile data
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Check if geodataframe is empty
    if gdf.empty:
        return False, "GeoDataFrame contains no features"
    
    # Check for valid geometries
    invalid_geoms = gdf[~gdf.geometry.is_valid]
    if not invalid_geoms.empty:
        return False, f"GeoDataFrame contains {len(invalid_geoms)} invalid geometries"
    
    # Check for Z dimension
    if gdf.geometry.apply(lambda geom: geom.has_z if geom is not None else False).any():
        return False, "GeoDataFrame contains 3D geometries (Z values), which are not supported"
        
    return True, ""

def get_geometry_type(gdf:GeoDataFrame) -> str:
    """
    Determine the geometry type from a GeoDataFrame
    
    Args:
        gdf: GeoDataFrame with the shapefile data
        
    Returns:
        str: One of 'point', 'line', 'polygon' or raises error
    """
    # Get unique geometry types (there might be multiple)
    geom_types = gdf.geom_type.unique()
    
    # Check for mixed geometry types
    if len(geom_types) > 1:
        print(f"Mixed geometry types detected: {geom_types}")
    
    # Use the first/predominant type for classification
    geometry_type = geom_types[0].lower()
    
    geometry_mapping = {
        'point': 'point',
        'multipoint': 'multipoint',
        'linestring': 'linestring',
        'multilinestring': 'multilinestring',
        'polygon': 'polygon',
        'multipolygon': 'multipolygon'
    }
    
    if geometry_type in geometry_mapping:
        return geometry_mapping[geometry_type]
    else:
        raise GeoFrameValidationError(f"Unsupported geometry type: {geometry_type}")
    