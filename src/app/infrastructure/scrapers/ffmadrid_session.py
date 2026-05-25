"""HTTP session that logs into the ffmadrid.es federation portal."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup


HTML_ENCODING = "iso-8859-15"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class LoginError(RuntimeError):
    """Raised when login does not produce an authenticated session."""


@dataclass(frozen=True)
class FfmadridCredentials:
    """Username and password for the federation portal."""

    user: str
    password: str


class FfmadridSession:
    """Authenticated session against ``aranjuez.ffmadrid.es``.

    Calling ``get_html(url)`` returns the decoded HTML for ``url``. The session
    transparently performs a login the first time an unauthenticated page is
    detected.
    """

    def __init__(
        self,
        base_url: str,
        credentials: FfmadridCredentials,
        *,
        verify_tls: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._credentials = credentials
        self._verify_tls = verify_tls
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
        self._authenticated = False

    def get_html(self, url: str) -> str:
        """Return the HTML body of ``url`` decoded as ISO-8859-15."""

        html = self._fetch(url)
        if self._looks_like_login(html):
            self._login(html)
            html = self._fetch(url)
            if self._looks_like_login(html):
                raise LoginError(
                    "Login did not grant access — credentials may be invalid"
                )
            self._authenticated = True
        return html

    def _fetch(self, url: str) -> str:
        response = self._session.get(
            url,
            timeout=self._timeout,
            allow_redirects=True,
            verify=self._verify_tls,
        )
        response.raise_for_status()
        return response.content.decode(HTML_ENCODING, errors="replace")

    def _looks_like_login(self, html: str) -> bool:
        lowered = html.lower()
        return 'type="password"' in lowered and ("usuario" in lowered or "user" in lowered)

    def _login(self, login_page_html: str) -> None:
        action, user_field, pass_field, hidden = self._extract_form(login_page_html)
        login_url = self._resolve_url(action)
        payload = {**hidden, user_field: self._credentials.user, pass_field: self._credentials.password}
        response = self._session.post(
            login_url,
            data=payload,
            timeout=self._timeout,
            allow_redirects=True,
            verify=self._verify_tls,
        )
        response.raise_for_status()

    def _extract_form(
        self, html: str
    ) -> tuple[str, str, str, dict[str, str]]:
        soup = BeautifulSoup(html, "html.parser")
        password_input = soup.find("input", attrs={"type": "password"})
        if password_input is None:
            raise LoginError("Could not locate password field in login page")
        form = password_input.find_parent("form")
        if form is None:
            raise LoginError("Password input is not enclosed in a <form>")
        user_input = form.find("input", attrs={"type": re.compile(r"^(text|email)?$", re.I)})
        if user_input is None or not user_input.get("name"):
            raise LoginError("Could not locate username field in login form")
        action = form.get("action") or ""
        hidden = {
            inp.get("name"): inp.get("value", "")
            for inp in form.find_all("input", attrs={"type": "hidden"})
            if inp.get("name")
        }
        return action, user_input["name"], password_input.get("name", "NPass"), hidden

    def _resolve_url(self, candidate: str) -> str:
        if candidate.startswith("http"):
            return candidate
        if candidate.startswith("/"):
            return f"{self._base_url}{candidate}"
        return f"{self._base_url}/{candidate}"
