from typing import List, Dict, Any, Optional

from landreg.exceptions import TableNotFoundError

from landreg.services.database_service import get_table_columns

def type_compatible(source_type: str, target_type: str) -> bool:
    """Check if column types are compatible for mapping"""
    # Define type compatibility groups
    numeric_types = {'integer', 'bigint', 'smallint', 'numeric', 'decimal', 'real', 'double precision'}
    text_types = {'character varying', 'varchar', 'text', 'char', 'character'}
    date_types = {'timestamp', 'timestamp with time zone', 'timestamp without time zone', 'date', 'time'}
    boolean_types = {'boolean', 'bool'}
    geometry_types = {'USER-DEFINED'}  # PostGIS geometry types
    
    source_type = source_type.lower()
    target_type = target_type.lower()
    
    # Same type is always compatible
    if source_type == target_type:
        return True
        
    # Check type groups
    for type_group in [numeric_types, text_types, date_types, boolean_types, geometry_types]:
        if source_type in type_group and target_type in type_group:
            return True
            
    return False

def get_status_code(mapping_summary: Dict[str, int]) -> int:
    """
    Get status code based on validation results.
    
    Returns:
        1: Valid without warnings
        0: Valid with warnings  
        -1: Invalid (has errors)
    """
    if mapping_summary['invalid_mappings'] > 0:
        return -1
    elif mapping_summary['mappings_with_warnings'] > 0:
        return 0
    else:
        return 1

def validate_cadaster_column_mapping(
    source_table_name: str, 
    source_table_schema: str,
    matched_fields: List[Dict[str, str]]
) -> Dict[str, Any]:
    """
    Validate column mapping between source table and landreg_cadaster table.
    
    Args:
        source_table_name: Name of the source table
        source_table_schema: Schema of the source table
        matched_fields: List of column mappings
        
    Returns:
        Dictionary with validation results
        
    Raises:
        TableNotFoundError: When source table is not found
        DatabaseError: When there's a database error
    """
    # Fixed destination table
    destination_table_name = "landreg_cadaster"
    destination_table_schema = "public"
    
    # Get columns for both tables
    try:
        source_columns = get_table_columns(source_table_name, source_table_schema)
        destination_columns = get_table_columns(destination_table_name, destination_table_schema)
    except TableNotFoundError as e:
        if source_table_name in str(e):
            raise TableNotFoundError(f"جدول مبدا '{source_table_name}' در اسکیما '{source_table_schema}' یافت نشد")
        else:
            raise TableNotFoundError(f"جدول مقصد '{destination_table_name}' در اسکیما '{destination_table_schema}' یافت نشد")
    
    # Create lookup dictionaries for faster access
    source_column_lookup = {col['name']: col for col in source_columns}
    destination_column_lookup = {col['name']: col for col in destination_columns}
    
    # Validation results
    valid_mappings = []
    invalid_mappings = []
    warnings = []
    
    # Track used columns to detect duplicates
    used_source_columns = set()
    used_destination_columns = set()
    
    for i, mapping in enumerate(matched_fields):
        old_col = mapping.get('old_cadaster_col')
        new_col = mapping.get('landreg_cadaster_col')
        
        mapping_result = {
            'index': i,
            'old_cadaster_col': old_col,
            'landreg_cadaster_col': new_col,
            'errors': [],
            'warnings': []
        }
        
        # Basic validation
        if not old_col or not new_col:
            mapping_result['errors'].append("هر دو فیلد 'old_cadaster_col' و 'landreg_cadaster_col' الزامی هستند")
            invalid_mappings.append(mapping_result)
            continue
        
        # Check if source column exists
        if old_col not in source_column_lookup:
            mapping_result['errors'].append(f"ستون مبدا '{old_col}' در جدول '{source_table_name}' یافت نشد")
        
        # Check if destination column exists
        if new_col not in destination_column_lookup:
            mapping_result['errors'].append(f"ستون مقصد '{new_col}' در جدول 'landreg_cadaster' یافت نشد")
        
        # Check for duplicate mappings
        if old_col in used_source_columns:
            mapping_result['warnings'].append(f"ستون مبدا '{old_col}' چندین بار نگاشت شده است")
        
        if new_col in used_destination_columns:
            mapping_result['warnings'].append(f"ستون مقصد '{new_col}' چندین بار نگاشت شده است")
        
        # If both columns exist, check type compatibility
        if old_col in source_column_lookup and new_col in destination_column_lookup:
            source_col_info = source_column_lookup[old_col]
            dest_col_info = destination_column_lookup[new_col]
            
            mapping_result['source_column_info'] = {
                'name': source_col_info['name'],
                'type': source_col_info['type'],
                'nullable': source_col_info['nullable']
            }
            
            mapping_result['destination_column_info'] = {
                'name': dest_col_info['name'],
                'type': dest_col_info['type'],
                'nullable': dest_col_info['nullable']
            }
            
            # Check type compatibility
            if not type_compatible(source_col_info['type'], dest_col_info['type']):
                mapping_result['warnings'].append(
                    f"عدم تطابق نوع داده: مبدا '{source_col_info['type']}' -> مقصد '{dest_col_info['type']}'"
                )
            
            # Check nullable constraints
            if not source_col_info['nullable'] and dest_col_info['nullable']:
                mapping_result['warnings'].append(
                    "نگاشت از ستون غیر قابل null به ستون قابل null (امکان از دست رفتن داده وجود دارد)"
                )
            elif source_col_info['nullable'] and not dest_col_info['nullable']:
                mapping_result['warnings'].append(
                    "نگاشت از ستون قابل null به ستون غیر قابل null (مقادیر NULL باعث خطا خواهند شد)"
                )
        
        # Track used columns
        if old_col:
            used_source_columns.add(old_col)
        if new_col:
            used_destination_columns.add(new_col)
        
        # Add to appropriate list
        if mapping_result['errors']:
            invalid_mappings.append(mapping_result)
        else:
            valid_mappings.append(mapping_result)
            if mapping_result['warnings']:
                warnings.extend(mapping_result['warnings'])
    
    # Find unmapped columns
    mapped_source_cols = {m['old_cadaster_col'] for m in valid_mappings}
    mapped_dest_cols = {m['landreg_cadaster_col'] for m in valid_mappings}
    
    unmapped_source_columns = [
        col for col in source_columns 
        if col['name'] not in mapped_source_cols
    ]
    
    unmapped_destination_columns = [
        col for col in destination_columns 
        if col['name'] not in mapped_dest_cols
    ]
    
    return {
        'source_table': {
            'name': source_table_name,
            'schema': source_table_schema,
            'total_columns': len(source_columns)
        },
        'destination_table': {
            'name': destination_table_name,
            'schema': destination_table_schema,
            'total_columns': len(destination_columns)
        },
        'mapping_summary': {
            'total_mappings': len(matched_fields),
            'valid_mappings': len(valid_mappings),
            'invalid_mappings': len(invalid_mappings),
            'mappings_with_warnings': len([m for m in valid_mappings if m.get('warnings')]),
            'unmapped_source_columns': len(unmapped_source_columns),
            'unmapped_destination_columns': len(unmapped_destination_columns)
        },
        'valid_mappings': valid_mappings,
        'invalid_mappings': invalid_mappings,
        'unmapped_source_columns': [col['name'] for col in unmapped_source_columns],
        'unmapped_destination_columns': [col['name'] for col in unmapped_destination_columns],
        'general_warnings': list(set(warnings))  # Remove duplicates
    }