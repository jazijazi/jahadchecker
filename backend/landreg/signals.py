from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.conf import settings

@receiver(post_migrate)
def publish_pelak_layers_after_migrate(sender, **kwargs):
    """
    After migrations run, publish specific PostGIS tables to GeoServer.
    """
    # Only run for your app, not every app
    if sender.name != "landreg":
        return

    # Import inside to avoid circular imports
    from geoserverapp.services.geoserver_service import GeoServerService
    from landreg.models.pelak import Pelak
    geoserver_service = GeoServerService()


    try:
        gs_result = geoserver_service.pulish_layer(
            workspace=settings.GEOSERVER['DEFAULT_WORKSPACE'],
            store_name=settings.GEOSERVER['DEFAULT_STORE'],
            pg_table=Pelak._meta.db_table,
            title=Pelak._meta.db_table,
        )
        print("GeoServer response for Pulish Pelak layer:", gs_result)
    except Exception as e:
        print("Failed to publish layerfor Pulish Pelak layer:", e)

@receiver(post_migrate)
def publish_cadaster_layers_after_migrate(sender, **kwargs):
    """
    After migrations run, publish specific PostGIS tables to GeoServer.
    """
    # Only run for your app, not every app
    if sender.name != "landreg":
        return

    # Import inside to avoid circular imports
    from geoserverapp.services.geoserver_service import GeoServerService
    from landreg.models.cadaster import Cadaster
    geoserver_service = GeoServerService()


    try:
        gs_result = geoserver_service.pulish_layer(
            workspace=settings.GEOSERVER['DEFAULT_WORKSPACE'],
            store_name=settings.GEOSERVER['DEFAULT_STORE'],
            pg_table=Cadaster._meta.db_table,
            title=Cadaster._meta.db_table,
        )
        print("GeoServer response for Pulish Cadaster layer:", gs_result)
    except Exception as e:
        print("Failed to publish layerfor Pulish Cadaster layer:", e)

@receiver(post_migrate)
def publish_flag_layers_after_migrate(sender, **kwargs):
    """
    After migrations run, publish specific PostGIS tables to GeoServer.
    """
    # Only run for your app, not every app
    if sender.name != "landreg":
        return

    # Import inside to avoid circular imports
    from geoserverapp.services.geoserver_service import GeoServerService
    from landreg.models.flag import Flag
    geoserver_service = GeoServerService()


    try:
        gs_result = geoserver_service.pulish_layer(
            workspace=settings.GEOSERVER['DEFAULT_WORKSPACE'],
            store_name=settings.GEOSERVER['DEFAULT_STORE'],
            pg_table=Flag._meta.db_table,
            title=Flag._meta.db_table,
        )
        print("GeoServer response for Pulish Flag layer:", gs_result)
    except Exception as e:
        print("Failed to publish layerfor Pulish Flag layer:", e)


