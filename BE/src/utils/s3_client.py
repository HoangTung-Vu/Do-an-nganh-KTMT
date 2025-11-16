"""
S3 Client - Interface with AWS S3 or S3-compatible storage (MinIO, etc.)
"""
import io
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, BinaryIO
import boto3
from botocore.exceptions import ClientError
from .logger import setup_logger
from .load_config import load_config

logger = setup_logger('s3_client', 's3.log')


class S3Client:
    """Client for S3 storage operations"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize S3 client
        
        Args:
            config: Configuration dict (if None, loads from config.yaml)
        """
        # Load config if not provided
        if config is None:
            config = load_config()
        
        s3_config = config.get('s3', {})
        
        self.bucket_name = s3_config.get('bucket_name', 'pdf-documents')
        self.region = s3_config.get('region', 'us-east-1')
        
        # Initialize boto3 S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=s3_config.get('endpoint_url'),
            aws_access_key_id=s3_config.get('access_key_id'),
            aws_secret_access_key=s3_config.get('secret_access_key'),
            region_name=self.region,
            use_ssl=s3_config.get('use_ssl', True)
        )
        
        logger.info(f"S3 client initialized: bucket={self.bucket_name}, region={self.region}")
        
        # Create bucket if it doesn't exist
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket '{self.bucket_name}' exists")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                try:
                    if self.region == 'us-east-1':
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                    else:
                        self.s3_client.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={'LocationConstraint': self.region}
                        )
                    logger.info(f"Created bucket '{self.bucket_name}'")
                except ClientError as create_error:
                    logger.error(f"Error creating bucket: {str(create_error)}")
                    raise
            else:
                logger.error(f"Error checking bucket: {str(e)}")
                raise
    
    def upload_file(
        self, 
        file_path: Union[str, Path], 
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to S3
        
        Args:
            file_path: Local file path to upload
            s3_key: S3 object key (path in bucket)
            metadata: Optional metadata to attach
            
        Returns:
            S3 object key
        """
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_file(
                str(file_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            logger.info(f"Uploaded file to s3://{self.bucket_name}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file object to S3
        
        Args:
            file_obj: File-like object to upload
            s3_key: S3 object key
            metadata: Optional metadata to attach
            
        Returns:
            S3 object key
        """
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            logger.info(f"Uploaded fileobj to s3://{self.bucket_name}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error uploading fileobj: {str(e)}")
            raise
    
    def download_file(self, s3_key: str, local_path: Union[str, Path]) -> str:
        """
        Download a file from S3
        
        Args:
            s3_key: S3 object key
            local_path: Local path to save file
            
        Returns:
            Local file path
        """
        try:
            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            logger.info(f"Downloaded s3://{self.bucket_name}/{s3_key} to {local_path}")
            return str(local_path)
            
        except ClientError as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise
    
    def download_fileobj(self, s3_key: str) -> io.BytesIO:
        """
        Download a file from S3 as BytesIO object
        
        Args:
            s3_key: S3 object key
            
        Returns:
            BytesIO object containing file data
        """
        try:
            file_obj = io.BytesIO()
            self.s3_client.download_fileobj(
                self.bucket_name,
                s3_key,
                file_obj
            )
            file_obj.seek(0)
            logger.debug(f"Downloaded s3://{self.bucket_name}/{s3_key} to memory")
            return file_obj
            
        except ClientError as e:
            logger.error(f"Error downloading fileobj: {str(e)}")
            raise
    
    def read_json(self, s3_key: str) -> Dict[str, Any]:
        """
        Read JSON file from S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Parsed JSON data
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            data = json.loads(response['Body'].read().decode('utf-8'))
            logger.debug(f"Read JSON from s3://{self.bucket_name}/{s3_key}")
            return data
            
        except ClientError as e:
            logger.error(f"Error reading JSON: {str(e)}")
            raise
    
    def write_json(
        self,
        s3_key: str,
        data: Dict[str, Any],
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Write JSON data to S3
        
        Args:
            s3_key: S3 object key
            data: Data to write as JSON
            metadata: Optional metadata
            
        Returns:
            S3 object key
        """
        try:
            json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
            
            extra_args = {'ContentType': 'application/json'}
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=json_bytes,
                **extra_args
            )
            logger.info(f"Wrote JSON to s3://{self.bucket_name}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error writing JSON: {str(e)}")
            raise
    
    def list_objects(self, prefix: str = '', delimiter: str = '') -> List[str]:
        """
        List objects in S3 bucket with given prefix
        
        Args:
            prefix: Prefix to filter objects
            delimiter: Delimiter for grouping (e.g., '/' for folders)
            
        Returns:
            List of object keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter=delimiter
            )
            
            keys = [obj['Key'] for obj in response.get('Contents', [])]
            logger.debug(f"Listed {len(keys)} objects with prefix '{prefix}'")
            return keys
            
        except ClientError as e:
            logger.error(f"Error listing objects: {str(e)}")
            raise
    
    def list_folders(self, prefix: str = '') -> List[str]:
        """
        List "folders" (common prefixes) in S3 bucket
        
        Args:
            prefix: Prefix to filter folders
            
        Returns:
            List of folder names (without prefix)
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            folders = [
                cp['Prefix'].rstrip('/').replace(prefix, '', 1)
                for cp in response.get('CommonPrefixes', [])
            ]
            logger.debug(f"Listed {len(folders)} folders with prefix '{prefix}'")
            return folders
            
        except ClientError as e:
            logger.error(f"Error listing folders: {str(e)}")
            raise
    
    def delete_object(self, s3_key: str):
        """
        Delete an object from S3
        
        Args:
            s3_key: S3 object key to delete
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted s3://{self.bucket_name}/{s3_key}")
            
        except ClientError as e:
            logger.error(f"Error deleting object: {str(e)}")
            raise
    
    def delete_folder(self, prefix: str):
        """
        Delete all objects with a given prefix (folder)
        
        Args:
            prefix: Folder prefix to delete
        """
        try:
            # List all objects with prefix
            objects = self.list_objects(prefix=prefix)
            
            if not objects:
                logger.info(f"No objects found with prefix '{prefix}'")
                return
            
            # Delete objects in batches
            for i in range(0, len(objects), 1000):
                batch = objects[i:i + 1000]
                delete_objects = [{'Key': key} for key in batch]
                
                self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={'Objects': delete_objects}
                )
            
            logger.info(f"Deleted {len(objects)} objects with prefix '{prefix}'")
            
        except ClientError as e:
            logger.error(f"Error deleting folder: {str(e)}")
            raise
    
    def object_exists(self, s3_key: str) -> bool:
        """
        Check if an object exists in S3
        
        Args:
            s3_key: S3 object key
            
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False
            else:
                logger.error(f"Error checking object existence: {str(e)}")
                raise
    
    def get_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        http_method: str = 'get_object'
    ) -> str:
        """
        Generate a presigned URL for accessing an S3 object
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds
            http_method: HTTP method ('get_object', 'put_object', etc.)
            
        Returns:
            Presigned URL
        """
        try:
            url = self.s3_client.generate_presigned_url(
                http_method,
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            logger.debug(f"Generated presigned URL for s3://{self.bucket_name}/{s3_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise
