import asyncio
import json
import logging
import socket
from typing import Dict, Optional, Any

_LOGGER = logging.getLogger(__name__)

class GofancoMatrixAPI:
    """API client for Gofanco HDMI Matrix with HTTP/0.9 support."""
    
    def __init__(self, host: str, port: int = 80):
        """Initialize the API client."""
        self.host = host
        self.port = port
        self._last_status = {}
        
    async def async_get_status(self) -> Optional[Dict[str, Any]]:
        """Get the current status of the matrix."""
        try:
            payload = '{"param1":"1"}'
            headers = "Content-Type: application/json;charset=UTF-8"
            
            response = await self._send_http09_request(payload, headers)
            if response:
                status = json.loads(response)
                self._last_status = status
                return status
                
        except Exception as e:
            _LOGGER.error("Error getting status: %s", e)
            
        return None
    
    async def async_set_output(self, output: int, input_source: int) -> bool:
        """Set an output to a specific input source."""
        try:
            payload = f"out{output}={input_source}"
            headers = "Content-Type: application/x-www-form-urlencoded"
            
            response = await self._send_http09_request(payload, headers)
            
            # Verify the change by getting status
            await asyncio.sleep(0.5)  # Give device time to process
            status = await self.async_get_status()
            
            if status:
                return status.get(f"out{output}") == str(input_source)
                
        except Exception as e:
            _LOGGER.error("Error setting output %s to input %s: %s", output, input_source, e)
            
        return False
    
    async def _send_http09_request(self, payload: str, content_type: str) -> Optional[str]:
        """Send HTTP/0.9 compatible request and handle malformed responses."""
        try:
            # Create socket connection
            reader, writer = await asyncio.open_connection(self.host, self.port)
            
            # Construct HTTP request
            request = (
                f"POST /inform.cgi HTTP/1.1\r\n"
                f"Host: {self.host}\r\n"
                f"{content_type}\r\n"
                f"Content-Length: {len(payload)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
                f"{payload}"
            )
            
            # Send request
            writer.write(request.encode())
            await writer.drain()
            
            # Read response - device returns malformed HTTP/0.9 responses
            response_data = await reader.read()
            writer.close()
            await writer.wait_closed()
            
            # Decode response
            response_text = response_data.decode('utf-8', errors='ignore')
            _LOGGER.debug("Raw response: %s", repr(response_text))
            
            # The device returns malformed responses - extract JSON directly
            # Look for JSON content (starts with '{' and ends with '}')
            json_start = response_text.find('{')
            if json_start >= 0:
                json_end = response_text.rfind('}')
                if json_end > json_start:
                    json_content = response_text[json_start:json_end + 1]
                    
                    # Validate it's proper JSON by attempting to parse
                    try:
                        json.loads(json_content)
                        return json_content
                    except json.JSONDecodeError as e:
                        _LOGGER.warning("Invalid JSON in response: %s", e)
            
            # If no valid JSON found, check if response contains expected keys
            # Sometimes the device may return just the raw JSON without any HTTP wrapper
            if any(key in response_text for key in ['out1', 'out2', 'out3', 'out4', 'powstatus']):
                # Try to extract what looks like JSON from the raw response
                # Remove any leading/trailing non-JSON characters
                cleaned_response = response_text.strip()
                if cleaned_response.startswith('{') and cleaned_response.endswith('}'):
                    try:
                        json.loads(cleaned_response)
                        return cleaned_response
                    except json.JSONDecodeError:
                        pass
            
            _LOGGER.warning("Could not extract valid JSON from response: %s", repr(response_text))
            return None
            
        except Exception as e:
            _LOGGER.error("Error sending HTTP/0.9 request: %s", e)
            return None
    
    async def async_test_connection(self) -> bool:
        """Test if the device is reachable."""
        status = await self.async_get_status()
        return status is not None
    
    @property
    def last_status(self) -> Dict[str, Any]:
        """Get the last known status."""
        return self._last_status.copy()
