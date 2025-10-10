"""Azure Blob Storage integration for podcast publishing."""
from pathlib import Path
from typing import Optional
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import AzureError


class AzureBlobUploader:
    """Handles uploading podcast files to Azure Blob Storage."""

    def __init__(self, connection_string: str, container_name: str = "podcast-files"):
        """
        Initialize Azure Blob uploader.

        Args:
            connection_string: Azure Storage connection string
            container_name: Name of the blob container
        """
        self.connection_string = connection_string
        self.container_name = container_name
        self.blob_service_client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Azure Blob Service client."""
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        except Exception as e:
            raise AzureError(f"Failed to initialize Azure client: {e}")

    def test_connection(self) -> bool:
        """Test connection to Azure Blob Storage."""
        try:
            # Try to get container properties
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            container_client.get_container_properties()
            return True
        except Exception:
            return False

    def upload_file(self, local_path: str, blob_name: Optional[str] = None) -> str:
        """
        Upload a file to Azure Blob Storage.

        Args:
            local_path: Local file path to upload
            blob_name: Blob name (if None, uses date-based path)

        Returns:
            Public URL of the uploaded blob
        """
        local_file = Path(local_path)
        if not local_file.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        # Generate blob name if not provided
        if blob_name is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
            blob_name = f"{date_str}/{local_file.name}"

        try:
            # Upload file
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )

            with open(local_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)

            # Return public URL
            return self.generate_blob_url(blob_name)

        except Exception as e:
            raise AzureError(f"Failed to upload {local_path}: {e}")

    def delete_file(self, blob_name: str) -> bool:
        """
        Delete a file from Azure Blob Storage.

        Args:
            blob_name: Name of the blob to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            blob_client.delete_blob()
            return True
        except Exception:
            return False

    def generate_blob_url(self, blob_name: str) -> str:
        """
        Generate public URL for a blob.

        Args:
            blob_name: Name of the blob

        Returns:
            Public URL of the blob
        """
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name,
            blob=blob_name
        )
        return blob_client.url

    def get_file_size(self, blob_name: str) -> Optional[int]:
        """
        Get the size of a blob in bytes.

        Args:
            blob_name: Name of the blob

        Returns:
            File size in bytes, or None if not found
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            properties = blob_client.get_blob_properties()
            return properties.size
        except Exception:
            return None

    def list_blobs(self, prefix: str = "") -> list:
        """
        List blobs in the container.

        Args:
            prefix: Optional prefix to filter blobs

        Returns:
            List of blob names
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]
        except Exception:
            return []