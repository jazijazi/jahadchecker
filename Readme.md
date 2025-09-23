# GeoHub - Django GIS Application

A Django-based Geographic Information System (GIS) application that integrates with GeoServer for spatial data management and visualization.

## Features

- **Spatial Data Management**: Handle geographic data including Pelaks (land parcels), Cadasters, and Flags
- **GeoServer Integration**: Automatic layer publishing to GeoServer
- **User Management**: Role-based access control with company affiliations
- **Geographic Validation**: PostGIS-powered spatial operations and validations
- **API Endpoints**: RESTful APIs for spatial data operations

## Prerequisites

- Python 3.8+
- PostgreSQL with PostGIS extension
- GeoServer 2.20+
- Docker (optional, for GeoServer)

## Installation & Setup

### 1. Environment Configuration

Copy the environment example file and configure your settings:

```bash
cp .env-example .env
```

### 2. Configure Environment Variables

Edit the `.env` file and set the following required variables:

```bash
# GeoServer Configuration
GEOSERVER_URL="http://geoserver:8080/geoserver"
GEOSERVER_ADMIN_PASSWORD="admin"
GEOSERVER_ADMIN_USER="admin"
GEOSERVER_DEFAULT_WORKSPACE="defautl_django_geohub"
GEOSERVER_DEFAULT_STORE="defautl_store_geohub"

# Database Configuration (add your database settings)
# DATABASE_URL=postgresql://username:password@localhost:5432/geohub
```

### 3. Setup Commands

⚠️ **Important**: Follow these commands in the exact order specified below:

#### Step 1: Create GeoServer Workspace
```bash
python manage.py createworkspace
```

#### Step 2: Create PostGIS Store
```bash
python manage.py createpostgisstore
```

#### Step 3: Run Database Migrations
```bash
python manage.py migrate
```

#### Step 4: Create Superuser
```bash
python manage.py createsuperuser
```

### 4. Layer Publishing (Optional)

The application automatically publishes layers to GeoServer after database migrations. However, if you need to manually publish layers, use these commands:

```bash
# Publish Flag layer
python manage.py publish_flag

# Publish Cadaster layer
python manage.py publish_cadaster

# Publish Pelak layer
python manage.py publish_pelak
```

## Command Execution Order

⚠️ **Critical**: The order of commands is essential for proper setup:

1. **First**: Create workspace and store in GeoServer
2. **Then**: Run migrations (this will automatically trigger layer publishing)
3. **Finally**: Create superuser and optionally publish layers manually

The workspace and store must exist before running migrations because the post-migration signals automatically publish model tables to GeoServer.

## Application Structure

### Main Models

- **Province**: Administrative divisions
- **Company**: Organizations with geographic permissions
- **Pelak**: Land parcels with polygon boundaries
- **Cadaster**: Cadastral units for land registration
- **Flag**: Point-based markers for geographic annotations

### User Roles

- **Superuser**: Full system access
- **Nazer Companies**: Can create and verify land parcels
- **Super Nazer Companies**: Extended permissions for oversight

### API Endpoints

The application provides RESTful APIs for:
- Pelak management (creation, verification)
- Flag management (point-based annotations)
- Cadaster operations
- Geographic data validation

## Development

### Running the Development Server

```bash
python manage.py runserver
```

### Testing

```bash
python manage.py test
```

## GeoServer Integration

The application automatically:
- Creates workspaces and data stores
- Publishes PostGIS layers
- Manages spatial data through GeoServer's REST API
- Handles coordinate reference systems (SRID 4326)

## Troubleshooting

### Common Issues

1. **GeoServer Connection Failed**
   - Verify GeoServer is running and accessible
   - Check GEOSERVER_URL in your .env file
   - Ensure admin credentials are correct

2. **Migration Errors**
   - Ensure workspace and store are created first
   - Check PostGIS extension is installed
   - Verify database permissions

3. **Layer Publishing Failed**
   - Check GeoServer logs
   - Verify PostGIS store connection
   - Ensure tables exist before publishing
