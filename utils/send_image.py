# utils/send_image.py

import base64
import io
import logging
from fastapi.responses import StreamingResponse
from fastapi import HTTPException, status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_base64_image(base64_string: str, media_type: str = "image/png") -> StreamingResponse:
    """
    Convert a base64 string to a streaming response for sending images to the frontend.
    This function is designed for real implementation, handling errors and ensuring proper image data processing.
    
    Args:
        base64_string (str): The base64 encoded string of the image. It can include the data URI prefix (e.g., 'data:image/png;base64,').
        media_type (str): The media type of the image (default is 'image/png'). This can be overridden if detected from the data URI.
    
    Returns:
        StreamingResponse: A streaming response containing the image data to be consumed by the frontend.
    
    Raises:
        HTTPException: If the base64 string is invalid or cannot be decoded properly.
    """
    try:
        # Check if the base64 string contains a data URI prefix (e.g., 'data:image/png;base64,')
        if "," in base64_string:
            header, base64_string = base64_string.split(",", 1)
            # Extract media type from the data URI if available
            if "data:" in header and ";base64" in header:
                media_type_part = header.split(";")[0].replace("data:", "")
                if media_type_part:
                    media_type = media_type_part
        # Decode the base64 string
        image_data = base64.b64decode(base64_string)
        # Convert to bytes IO for streaming
        image_io = io.BytesIO(image_data)
        # Return as streaming response with the appropriate media type
        return StreamingResponse(image_io, media_type=media_type)
    except Exception as e:
        logger.error(f"Error decoding base64 image string: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 image data: {str(e)}"
        )
