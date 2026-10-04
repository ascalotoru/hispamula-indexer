import base64
import threading
import time

import httpx


class HispamulaSession:
    """Cliente HTTP con sesión persistente (cookies) y throttling."""

    def __init__(self, base_url: str, username: str = "", password: str = "",
                 request_delay: float = 1.0, timeout: float = 30.0,
                 user_agent: str = "hispamula-indexer/0.1") -> None:
        self._client = httpx.Client(
            base_url=base_url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": user_agent},
        )
        self._delay = request_delay
        self._lock = threading.Lock()
        self._last = 0.0

        if username and password:
            # HSLOGIN = base64(user:pass). El login POST también lo establece,
            # pero esta vía evita una petición extra y es válida 30 días.
            token = base64.b64encode(f"{username}:{password}".encode()).decode()
            self._client.headers["Cookie"] = f"HSLOGIN={token}"

    def _throttle(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = self._delay - (now - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        self._throttle()
        response = self._client.get(path, params=params)
        response.raise_for_status()
        return response

    def login(self, username: str, password: str) -> httpx.Response:
        """Login explícito; refresca la sesión/cookies."""
        self._throttle()
        response = self._client.post(
            "/",
            data={"username": username, "password": password, "login": "Iniciar"},
        )
        response.raise_for_status()
        return response

    def authed(self) -> bool:
        """Indica si la sesión está autenticada según la cabecera x-hm-user."""
        response = self.get("/")
        return response.headers.get("x-hm-user", "???") != "???"

    def close(self) -> None:
        self._client.close()
