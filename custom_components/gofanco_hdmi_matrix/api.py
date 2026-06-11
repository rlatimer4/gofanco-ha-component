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
POST_SWITCH_DELAY = 3.0

# After a request times out, stop polling for this long. A timeout means the
# device's single-threaded server is busy (e.g. a save/recall from the web UI
# can hold it for >2 minutes); stacking more SYNs on it makes things worse.
TIMEOUT_BACKOFF = 120.0


class GofancoMatrixAPI:
    """API client for Gofanco HDMI Matrix with HTTP/0.9 support."""

    def __init__(self, host: str, port: int = 80):
        """Initialize the API client."""
        self.host = host
        self.port = port
        self._last_status: Dict[str, Any] = {}
        self._command_in_flight = False

        # Monotonic deadline before which polls should be skipped. Set after a
        # request times out so we leave the device alone while it recovers.
        self._backoff_until: float = 0.0

        # Semaphore ensures only one request is in-flight at a time,
        # preventing concurrent connections from stacking up on the device.
        self._request_lock = asyncio.Semaphore(1)

        # Tracks the monotonic time of the last completed request so we can
        # enforce a minimum gap between requests.
        self._last_request_time: float = 0.0

        # Set when Home Assistant is stopping; refuses new requests so we
        # never open a connection we might abandon mid-conversation.
        self._shutting_down = False

        # The currently running (shielded) request task, kept so shutdown
        # can wait for it to finish and close the socket gracefully.
        self._active_task: Optional[asyncio.Task] = None

    async def async_shutdown(self) -> None:
        """Drain the in-flight request before Home Assistant exits.

        Abandoning a request mid-conversation is what kills the device on
        HA restarts: its single-threaded server either blocks forever
        waiting for data that never arrives, or gets a TCP RST when it
        writes its response to our dead socket.
        """
        self._shutting_down = True
        task = self._active_task
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=10.0)
            except Exception:
                pass

    def should_skip_poll(self) -> bool:
        """Return True if the coordinator should skip this poll cycle."""
        if self._command_in_flight:
            return True
        return asyncio.get_event_loop().time() < self._backoff_until

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
        self._command_in_flight = True
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

        finally:
            self._command_in_flight = False

        return False

    async def _send_http09_request(
        self, payload: str, content_type: str
    ) -> Optional[str]:
        """Send HTTP/0.9 compatible request and handle malformed responses.

        Uses a semaphore to serialise all requests (no concurrent connections)
        and enforces a minimum inter-request interval to avoid exhausting the
        device's limited TCP connection table.
        """
        if self._shutting_down:
            _LOGGER.debug("Refusing new request — Home Assistant is stopping")
            return None

        async with self._request_lock:
            # If a previous request was cancelled but is still finishing in
            # the background (shielded), wait for it — never run two
            # connections against the device at once.
            prev = self._active_task
            if prev is not None and not prev.done():
                try:
                    await asyncio.wait_for(asyncio.shield(prev), timeout=15.0)
                except Exception:
                    pass

            # Enforce minimum gap between requests
            loop = asyncio.get_event_loop()
            now = loop.time()
            elapsed = now - self._last_request_time
            if elapsed < MIN_REQUEST_INTERVAL:
                await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)

            # Once started, a request must run to completion even if our
            # caller is cancelled (e.g. HA restarting). Abandoning the
            # conversation leaves the device's single-threaded server blocked
            # on a half-open socket or RSTs it mid-response — both kill the
            # web UI. asyncio.shield lets the task finish in the background;
            # async_shutdown() waits for it before the process exits.
            task = asyncio.ensure_future(self._do_request(payload, content_type))
            self._active_task = task
            try:
                result = await asyncio.shield(task)
            except asyncio.CancelledError:
                _LOGGER.debug(
                    "Caller cancelled — letting in-flight device request finish"
                )
                raise
            finally:
                # Keep the reference while the shielded task is still
                # running so shutdown (or the next request) can wait on it.
                if task.done():
                    self._active_task = None
                # Record completion time *after* the request so the interval
                # is measured from the end of one request to the next.
                self._last_request_time = loop.time()

        return result

    async def _do_request(
        self, payload: str, content_type: str
    ) -> Optional[str]:
        """Execute the raw TCP request. Called only from _send_http09_request."""
        reader = None
        writer = None
        request_failed = False

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10.0,
            )

            # Send the (tiny) request in a single immediate segment so the
            # device's single-threaded server never sits waiting on a
            # partially received request.
            sock = writer.get_extra_info("socket")
            if sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

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

            chunks = []
            accumulated = ""
            while True:
                chunk = await asyncio.wait_for(reader.read(4096), timeout=2.0)
                if not chunk:
                    break
                accumulated += chunk.decode("utf-8", errors="ignore")
                chunks.append(chunk)
                # Stop as soon as we have a balanced JSON object
                open_count = accumulated.count("{")
                close_count = accumulated.count("}")
                if open_count > 0 and open_count == close_count:
                    # Briefly wait for the device's own close (EOF) so our
                    # FIN arrives after it has finished sending, the same
                    # sequence a browser produces. Don't wait long if the
                    # device keeps the connection open.
                    try:
                        await asyncio.wait_for(reader.read(4096), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
                    break

            response_text = accumulated

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
            request_failed = True
            # The device's single-threaded server is busy (a save/recall from
            # the web UI can hold it for >2 minutes). Back off so we don't
            # stack more connections on it while it recovers.
            self._backoff_until = (
                asyncio.get_event_loop().time() + TIMEOUT_BACKOFF
            )
            _LOGGER.warning(
                "Timeout talking to device at %s:%s — backing off polls for %ss",
                self.host,
                self.port,
                TIMEOUT_BACKOFF,
            )
            return None
        except Exception as e:
            request_failed = True
            _LOGGER.error("Error sending HTTP/0.9 request: %s", e)
            return None
        finally:
            # On success, close gracefully (FIN/ACK) exactly like the device's
            # own web UI does — the device handles that fine indefinitely.
            # Only on failure do we force a TCP RST via SO_LINGER(on, 0):
            # the connection may be stuck on a busy device, and an abort frees
            # its connection slot immediately. Never RST healthy connections —
            # embedded TCP stacks can leak control blocks when a peer aborts
            # mid-close, which exhausts the pool and kills the web UI.
            if writer is not None:
                try:
                    if request_failed:
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
