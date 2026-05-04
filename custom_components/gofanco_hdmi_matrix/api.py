"""API client for Gofanco HDMI Matrix."""
import asyncio
import json
import logging
import socket
import struct
from typing import Dict, Optional, Any

_LOGGER = logging.getLogger(__name__)

# Minimum time (seconds) to wait between any two consecutive requests.
# Prevents bursting multiple connections at the device's embedded HTTP server.
MIN_REQUEST_INTERVAL = 2.0

# How long to wait after a switch command before verifying the change.
# The device needs time to process; 0.5s was too short.
POST_SWITCH_DELAY = 2.0


class GofancoMatrixAPI:
    """API client for Gofanco HDMI Matrix with HTTP/0.9 support."""

    def __init__(self, host: str, port: int = 80):
        """Initialize the API client."""
        self.host = host
        self.port = port
        self._last_status: Dict[str, Any] = {}

        # Semaphore ensures only one request is in-flight at a time,
        # preventing concurrent connections from stacking up on the device.
        self._request_lock = asyncio.Semaphore(1)

        # Tracks the monotonic time of the last completed request so we can
        # enforce a minimum gap between requests.
        self._last_request_time: float = 0.0

    async def async_get_status(self) -> Optional[Dict[str, Any]]:
        """Get the current status of the matrix."""
        try:
            payload = '{"param1":"1"}'
            content_type = "Content-Type: application/json;charset=UTF-8"

            response = await self._send_http09_request(payload, content_type)
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
            content_type = "Content-Type: application/x-www-form-urlencoded"

            response = await self._send_http09_request(payload, content_type)

            # Give the device adequate time to process the switch command
            # before querying status. 0.5s was insufficient for this hardware.
            await asyncio.sleep(POST_SWITCH_DELAY)

            status = await self.async_get_status()
            if status:
                return status.get(f"out{output}") == str(input_source)

        except Exception as e:
            _LOGGER.error(
                "Error setting output %s to input %s: %s", output, input_source, e
            )

        return False

    async def _send_http09_request(
        self, payload: str, content_type: str
    ) -> Optional[str]:
        """Send HTTP/0.9 compatible request and handle malformed responses.

        Uses a semaphore to serialise all requests (no concurrent connections)
        and enforces a minimum inter-request interval to avoid exhausting the
        device's limited TCP connection table.
        """
        async with self._request_lock:
            # Enforce minimum gap between requests
            loop = asyncio.get_event_loop()
            now = loop.time()
            elapsed = now - self._last_request_time
            if elapsed < MIN_REQUEST_INTERVAL:
                await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)

            result = await self._do_request(payload, content_type)

            # Record completion time *after* the request so the interval is
            # measured from the end of one request to the start of the next.
            self._last_request_time = loop.time()

        return result

    async def _do_request(
        self, payload: str, content_type: str
    ) -> Optional[str]:
        """Execute the raw TCP request. Called only from _send_http09_request."""
        reader = None
        writer = None

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10.0,
            )

            request = (
                f"POST /inform.cgi HTTP/1.1\r\n"
                f"Host: {self.host}\r\n"
                f"{content_type}\r\n"
                f"Content-Length: {len(payload)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
                f"{payload}"
            )

            writer.write(request.encode())
            await writer.drain()

            response_data = await asyncio.wait_for(
                reader.read(),
                timeout=5.0,
            )

            response_text = response_data.decode("utf-8", errors="ignore")

            if _LOGGER.isEnabledFor(logging.DEBUG):
                _LOGGER.debug("Raw response length: %d bytes", len(response_text))

            # The device returns malformed HTTP responses — extract JSON directly.
            json_start = response_text.find("{")
            if json_start >= 0:
                json_end = response_text.rfind("}")
                if json_end > json_start:
                    json_content = response_text[json_start : json_end + 1]
                    try:
                        json.loads(json_content)
                        return json_content
                    except json.JSONDecodeError as e:
                        _LOGGER.warning("Invalid JSON in response: %s", e)

            # Fallback: sometimes the device returns raw JSON with no HTTP wrapper.
            if any(
                key in response_text
                for key in ["out1", "out2", "out3", "out4", "powstatus"]
            ):
                cleaned = response_text.strip()
                if cleaned.startswith("{") and cleaned.endswith("}"):
                    try:
                        json.loads(cleaned)
                        return cleaned
                    except json.JSONDecodeError:
                        pass

            _LOGGER.warning("Could not extract valid JSON from response")
            return None

        except asyncio.TimeoutError:
            _LOGGER.error(
                "Timeout connecting to device at %s:%s", self.host, self.port
            )
            return None
        except Exception as e:
            _LOGGER.error("Error sending HTTP/0.9 request: %s", e)
            return None
        finally:
            # Always close the connection to prevent leaks.
            # Setting SO_LINGER(on, timeout=0) forces a TCP RST instead of a
            # graceful FIN/ACK sequence. This releases the connection slot on
            # the device's limited TCP table immediately rather than leaving it
            # in TIME_WAIT, which is the primary cause of the web UI crashing.
            if writer is not None:
                try:
                    sock = writer.get_extra_info("socket")
                    if sock:
                        sock.setsockopt(
                            socket.SOL_SOCKET,
                            socket.SO_LINGER,
                            struct.pack("ii", 1, 0),
                        )
                    writer.close()
                    await writer.wait_closed()
                except Exception as e:
                    _LOGGER.debug("Error closing writer: %s", e)

    async def async_test_connection(self) -> bool:
        """Test if the device is reachable."""
        status = await self.async_get_status()
        return status is not None

    @property
    def last_status(self) -> Dict[str, Any]:
        """Get the last known status."""
        return self._last_status.copy()
