"""
Streaming file upload utilities for memory-efficient file handling.
"""

import hashlib
import logging
from pathlib import Path
from typing import AsyncGenerator, Optional, Tuple

import aiofiles
from fastapi import UploadFile

logger = logging.getLogger(__name__)


class StreamingFileProcessor:
    """Process uploaded files in chunks to avoid memory exhaustion."""
    
    def __init__(
        self,
        chunk_size: int = 1024 * 1024,  # 1MB chunks by default
        max_file_size: Optional[int] = None
    ):
        """
        Initialize streaming file processor.
        
        Args:
            chunk_size: Size of chunks to process (in bytes)
            max_file_size: Optional maximum file size limit (in bytes)
        """
        self.chunk_size = chunk_size
        self.max_file_size = max_file_size
    
    async def process_upload(
        self,
        file: UploadFile,
        destination: Path
    ) -> Tuple[str, int]:
        """
        Process an uploaded file in streaming fashion.
        
        Args:
            file: FastAPI UploadFile instance
            destination: Destination path to save the file
            
        Returns:
            Tuple of (file_hash, total_size)
            
        Raises:
            ValueError: If file exceeds max_file_size
        """
        hasher = hashlib.sha256()
        total_size = 0
        
        # Ensure destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            async with aiofiles.open(destination, 'wb') as f:
                while chunk := await file.read(self.chunk_size):
                    chunk_bytes = chunk if isinstance(chunk, bytes) else chunk.encode()
                    
                    # Update hash
                    hasher.update(chunk_bytes)
                    
                    # Track size
                    chunk_size = len(chunk_bytes)
                    total_size += chunk_size
                    
                    # Check size limit
                    if self.max_file_size and total_size > self.max_file_size:
                        # Clean up partial file
                        await f.close()
                        destination.unlink(missing_ok=True)
                        raise ValueError(
                            f"File size exceeds limit of {self.max_file_size} bytes "
                            f"(current: {total_size} bytes)"
                        )
                    
                    # Write chunk
                    await f.write(chunk_bytes)
            
            file_hash = hasher.hexdigest()
            
            logger.info(
                f"Processed upload: {file.filename} -> {destination} "
                f"(size: {total_size} bytes, hash: {file_hash[:16]}...)"
            )
            
            return file_hash, total_size
            
        except Exception as e:
            logger.error(f"Error processing upload {file.filename}: {e}")
            # Clean up on error
            if destination.exists():
                destination.unlink(missing_ok=True)
            raise
    
    async def stream_file_chunks(
        self,
        file_path: Path
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream file contents in chunks.
        
        Args:
            file_path: Path to file to stream
            
        Yields:
            File chunks as bytes
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(self.chunk_size):
                yield chunk
    
    async def compute_file_hash(
        self,
        file_path: Path,
        algorithm: str = 'sha256'
    ) -> str:
        """
        Compute file hash in streaming fashion.
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm ('md5', 'sha256', etc.)
            
        Returns:
            Hex digest of file hash
        """
        hasher = hashlib.new(algorithm)
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(self.chunk_size):
                hasher.update(chunk)
        
        return hasher.hexdigest()


async def process_multipart_upload(
    file: UploadFile,
    destination_dir: Path,
    chunk_size: int = 1024 * 1024,
    max_file_size: Optional[int] = None
) -> dict:
    """
    Convenience function to process a multipart file upload.
    
    Args:
        file: Uploaded file
        destination_dir: Directory to save file
        chunk_size: Size of processing chunks
        max_file_size: Optional maximum file size
        
    Returns:
        Dictionary with file metadata (path, hash, size, etc.)
    """
    processor = StreamingFileProcessor(
        chunk_size=chunk_size,
        max_file_size=max_file_size
    )
    
    # Generate safe filename
    filename = file.filename or "uploaded_file"
    destination = destination_dir / filename
    
    # Process upload
    file_hash, total_size = await processor.process_upload(file, destination)
    
    # Detect content type if not provided
    content_type = file.content_type or "application/octet-stream"
    
    return {
        "filename": filename,
        "path": str(destination),
        "hash": file_hash,
        "size": total_size,
        "content_type": content_type
    }


__all__ = [
    "StreamingFileProcessor",
    "process_multipart_upload",
]
