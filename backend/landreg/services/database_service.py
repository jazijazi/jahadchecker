import re 

from typing import Tuple, Dict, Any, Optional , List  , TypedDict
from sqlalchemy import create_engine , Engine , text
from urllib.parse import quote_plus
from django.conf import settings
from sqlalchemy.exc import SQLAlchemyError

from landreg.exceptions import (
    SqlAlchemyEnginError,
    TableNotFoundError,
    DatabaseError,
)

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

def get_table_columns(table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get columns and types of a PostGIS table.
    
    Args:
        table_name: Name of the table to inspect
        schema: Optional schema name (defaults to public schema)
    
    Returns:
        List of dictionaries containing column information
        
    Raises:
        TableNotFoundError: When table is not found
        DatabaseError: When there's a database connection or query error
    """
    if not table_name or not isinstance(table_name, str):
        raise ValueError("table_name must be a non-empty string")
    
    # Sanitize table name to prevent SQL injection
    table_name = table_name.strip()
    if not table_name:
        raise ValueError("table_name cannot be empty")
    
    engine = create_new_database_engine()
    
    try:
        # First check if table exists
        table_exists_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
                AND table_schema = COALESCE(:schema, 'public')
            )
        """)
        
        # Get columns query
        columns_query = text("""
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_name = :table_name
            AND table_schema = COALESCE(:schema, 'public')
            ORDER BY ordinal_position
        """)
        
        with engine.connect() as conn:
            # Check if table exists
            table_exists = conn.execute(
                table_exists_query, 
                {"table_name": table_name, "schema": schema}
            ).scalar()
            
            if not table_exists:
                raise TableNotFoundError(f"جدول '{table_name}' در دیتابیس یافت نشد")
            
            # Get columns
            result = conn.execute(
                columns_query, 
                {"table_name": table_name, "schema": schema}
            )
            
            columns = []
            for row in result:
                column_info = {
                    "name": row.column_name,
                    "type": row.data_type,
                    "nullable": row.is_nullable == 'YES',
                }
                
                # Add optional fields if they exist
                if row.column_default is not None:
                    column_info["default"] = row.column_default
                if row.character_maximum_length is not None:
                    column_info["max_length"] = row.character_maximum_length
                if row.numeric_precision is not None:
                    column_info["precision"] = row.numeric_precision
                if row.numeric_scale is not None:
                    column_info["scale"] = row.numeric_scale
                    
                columns.append(column_info)
            
            return columns
            
    except TableNotFoundError:
        raise  # Re-raise our custom exception
    except SQLAlchemyError as e:
        raise DatabaseError(f"Database query failed: {e}")
    except Exception as e:
        raise DatabaseError(f"Unexpected error while fetching table columns: {e}")
