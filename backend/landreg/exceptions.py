class GeoDatabaseValidationError(Exception):
    """Exception raised for errors in the geodatabase validation."""
    pass 

class SqlAlchemyEnginError(Exception):
    """Exception raised for errors in the geodatabase validation."""
    pass 

class GeoFrameValidationError(Exception):
    """Exception raised for errors in the geoframe validation."""
    pass

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

class TableNotFoundError(DatabaseError):
    """Exception raised when table is not found"""
    pass

class CadasterImportError(Exception):
    """Exception raised during cadaster import"""
    pass
