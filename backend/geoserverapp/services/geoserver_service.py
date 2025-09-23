import requests
import io
import os
import uuid
import tempfile
# from xml.dom import minidom
from lxml import etree
import xml.sax.saxutils as saxutils
from typing import Optional, Dict, Any
from django.core.files.uploadedfile import InMemoryUploadedFile
from geo.Geoserver import Geoserver , GeoserverException
from django.conf import settings

class GeoServerService:
    """Service class for interacting with GeoServer"""
    
    def __init__(self, url: str|None = None, username: str|None = None, password: str|None = None) -> None:
        # Use provided values or fallback to settings
        self.url = url or settings.GEOSERVER.get('URL')
        self.username = username or settings.GEOSERVER.get('USER')
        self.password = password or settings.GEOSERVER.get('PASSWORD')
        # Initialize Geoserver client
        self.geo      : Geoserver = Geoserver(self.url, username=self.username, password=self.password)

    def get_all_layers_from_geoserver(
        self,
        workspace: str
    ) -> Dict:
        if not workspace :
            raise ValueError("workspace cannot be None!")
        res : Dict = self.geo.get_layers(workspace)
        return res
    
    def get_a_layer_from_geoserver(
        self,
        layername: str,
        workspace: str,
    ) -> Dict:
        if not workspace or not layername:
            raise ValueError("workspace and layername cannot be None!")
        
        res:Dict = self.geo.get_layer(layer_name=layername , workspace=workspace)
        return res
    
    def delete_a_layer_from_geoserver(
        self,
        layername: str,
        workspace: str,
    ) -> str:
        if not workspace or not layername:
            raise ValueError("workspace and layername cannot be None!")

        res:str = self.geo.delete_layer(layer_name=layername , workspace=workspace)
        return res
    
    def workspace_exists(
        self,
        workspace_name: str
    ) -> bool:
        """Check if a workspace exists"""
        try:
            result : Dict[str, Any] = self.geo.get_workspace(workspace=workspace_name)
            # If we got here without an exception, and there's a workspace element, it exists
            exists : bool = result.get("workspace") is not None
            return exists
        except Exception:
            # If there's an exception, assume the workspace doesn't exist
            return False
        
    def store_exists(
        self,
        store_name: str,
        workspace: str
    ) -> bool:
        if not store_name or not workspace:
            raise ValueError("Store name and workspace cannot be None or empty")            
        try:
            result : Dict[str, Any] = self.geo.get_featurestore(store_name=store_name, workspace=workspace)
            # If we got here without an exception, and there's a dataStore element, it exists
            exists : bool = result.get("name") is not None and result.get("enabled") is True
            return exists
        except Exception as e:
            return False
    
    def create_workspace(
        self,
        workspace_name: str
    ) -> Dict[str, Any]:
        """Create a new workspace"""
        if not workspace_name:
            raise ValueError("workspace name cannot be None!")
        
        # Check if workspace already exists
        if self.workspace_exists(workspace_name):
            try:
                # Try to get creation date if available
                workspace_info : Dict[str, Any] = self.geo.get_workspace(workspace=workspace_name)
                date_created:str = workspace_info.get("workspace", {}).get("dateCreated", "unknown date")
                raise Exception(f"Workspace '{workspace_name}' already exists (created on: {date_created})")
            except Exception as e:
                # If we can't get the date, just mention it exists
                if "already exists" not in str(e):
                    raise Exception(f"Workspace '{workspace_name}' already exists")
                else:
                    raise e
        
        # Workspace doesn't exist, so create it
        return self.geo.create_workspace(workspace=workspace_name)
    
    def create_postgis_store(
        self,
        store_name: str,
        workspace: str,
        db_params: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a PostGIS datastore"""
        if db_params is None:
            db_params = settings.DATABASES['default']

        if not store_name or not workspace:
            raise ValueError("store_name and workspace must have value")
        
        if not self.workspace_exists(workspace_name=workspace):
            raise Exception(f"workspace {workspace} dose not exist!")
                
        if self.store_exists(store_name=store_name, workspace=workspace):
            raise Exception(f"Store '{store_name}' already exists")
        
        # Escape XML special chars in password
        safe_password = saxutils.escape(db_params.get("PASSWORD", ""))
        
        return self.geo.create_featurestore(
            store_name=store_name,
            workspace=workspace,
            # port=db_params.get('PORT'),
            port=5432, # contaners database & geoserver both are in the same network
            db=db_params.get('NAME' , ''),
            # host=db_params.get('HOST'),
            host='jahad_postgis_db', #running in container
            pg_user=db_params.get('USER' , ''),
            pg_password=safe_password
        )
    
    def pulish_layer(
        self,
        workspace: str,
        store_name: str,
        title:str,
        pg_table: str,
    )-> Dict[str,str]:
        
        if not workspace or not store_name or not title or not pg_table:
            raise ValueError("workspace,store_name,title,pg_table cannot be None!")
        
        if not self.store_exists(store_name=store_name,workspace=workspace):
            raise Exception(f"Store '{store_name}' dose not exists")
    
        result : int = self.geo.publish_featurestore(
            workspace=workspace,
            store_name=store_name,
            title=title,
            pg_table=pg_table,
        )

        if result == 201:
            return {"detail":"The layer has been published successfully.","status":201}
        else:
            return {"detail":"Unknow Error","status":400}
    
    def download_layer_as_shape_zip(
        self,
        workspace: str,
        layer_name: str,
        bbox: Optional[str] = None,
        cql_filter: Optional[str] = None
    )->str:
        """
        Download a layer as a ZIP file with optional spatial and attribute filtering.
        
        - This is achieved via a direct request to GeoServer,
        as the geoserver-rest package does not currently support this functionality.

        Returns:
        - The file path of the downloaded ZIP archive located in the temporary directory.
        """
        
        FORMAT = "SHAPE-ZIP"
        
        if not workspace or not layer_name:
            raise ValueError("Workspace and layer_name cannot be None or empty")
        
        if not self.workspace_exists(workspace):
            raise GeoserverException(message="Workspace dose not exist!",status=404)

        
        wfs_url = f"{self.url}/wfs"
        params = {
            'service': 'WFS',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeNames': f"{workspace}:{layer_name}",
            'outputFormat': FORMAT,
        }

        if bbox:
            params['bbox'] = bbox
    
        if cql_filter:
            params['CQL_FILTER'] = cql_filter

        response = requests.get(
            wfs_url,
            params=params,
            auth=(self.username, self.password),
            stream=True
        )

        if response.status_code != 200:
            raise Exception(f"Failed to download layer: {response.status_code} - {response.text}")
        
        downloads_dir = os.path.join(settings.MEDIA_ROOT, "geoserverdownloads")
        os.makedirs(downloads_dir, exist_ok=True)

        # Generate a random UUID for the filename
        random_filename = f"{uuid.uuid4()}.zip"
        relative_path = os.path.join("geoserverdownloads", random_filename)
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        # Save the response content to the specified path
        with open(absolute_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return absolute_path

    def upload_sld_file_raw(
        self,
        sld_file,
        style_name: str,
        layername: str,
        workspace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uploads an SLD file to GeoServer using the REST API with raw=true.
        It modifies the NamedLayer Name in the SLD to match the layername.
        Then forces GeoServer to reload the style using a PUT request.

        Args:
            sld_file: A file-like object containing the SLD XML.
            style_name: The name to give the style in GeoServer.
            layername: The name of the layer that the style will apply to.
            workspace: Optional workspace to upload the style into.

        Returns:
            A dictionary indicating success or failure.
        """

        def fix_sld_named_layer_name(sld_file_obj, new_layer_name: str) -> bytes:
            sld_file_obj.seek(0)
            parser = etree.XMLParser(remove_blank_text=True)
            tree = etree.parse(sld_file_obj, parser)

            nsmap = {
                'sld': 'http://www.opengis.net/sld',
                'se': 'http://www.opengis.net/se'
            }

            name_elem = tree.find('.//se:Name', namespaces=nsmap)
            if name_elem is not None:
                name_elem.text = new_layer_name

            # Force use of "se" prefix
            etree.register_namespace("se", nsmap["se"])

            return etree.tostring(tree, pretty_print=True, encoding="utf-8", xml_declaration=True)

        fixed_sld_content = fix_sld_named_layer_name(sld_file, layername)
        # sld_file.seek(0)
        # sld_content = sld_file.read()

        # Upload URL
        url = f"{self.url}/rest"
        if workspace:
            url += f"/workspaces/{workspace}/styles"
        else:
            url += "/styles"

        # POST (raw SLD)
        post_response = requests.post(
            url,
            params={"name": style_name, "raw": "true"},
            auth=(self.username, self.password),
            headers={"Content-Type": "application/vnd.ogc.sld+xml"},
            data=fixed_sld_content
        )

        if post_response.status_code not in [200, 201]:
            raise Exception(f"Failed to upload SLD: {post_response.status_code} - {post_response.text}")

        # PUT (force reload without GeoServer changing the content)
        style_url = f"{self.url}/rest"
        if workspace:
            style_url += f"/workspaces/{workspace}/styles/{style_name}"
        else:
            style_url += f"/styles/{style_name}"

        put_response = requests.put(
            style_url,
            params={"raw": "true"},  # ✅ Critical fix
            auth=(self.username, self.password),
            headers={"Content-Type": "application/vnd.ogc.sld+xml"},
            data=fixed_sld_content
        )

        if put_response.status_code not in [200, 201]:
            raise Exception(f"Failed to force reload SLD: {put_response.status_code} - {put_response.text}")

        return {
            "success": True,
            "message": "SLD uploaded and activated successfully."
        }

    def apply_sld_to_layer(
        self,
        workspace: str,
        layer_name: str,
        style_name: str
    ) -> Dict[str, Any]:
        """
        Apply an existing style to a layer using GeoServer REST API.
        """
        url = f"{self.url}/rest/layers/{workspace}:{layer_name}"

        payload = f"""
        <layer>
        <defaultStyle>
            <name>{style_name}</name>
        </defaultStyle>
        </layer>
        """.strip()

        response = requests.put(
            url,
            data=payload.encode('utf-8'),
            headers={"Content-Type": "application/xml"},
            auth=(self.username, self.password)
        )

        if response.status_code in [200, 201]:
            return {
                "success": True,
                "message": "Style applied successfully to layer."
            }
        else:
            return {
                "success": False,
                "message": f"Failed to apply style: {response.status_code} - {response.text}"
            }
