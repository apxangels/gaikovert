"""
Тонкий клиент к Guacamole REST API.

Механика подтверждена вручную на реальном Guacamole 1.5.5 (docker compose,
сервисы guacamole/guacd/guacamole-db) перед тем, как это было написано:

- Sharing profiles (share-ссылки) здесь НЕ подходят: Guacamole выдаёт
  share-ссылку (`sharingCredentials`) только для уже АКТИВНОГО подключения —
  то есть кто-то должен быть реально подключён прямо сейчас. Кандидат
  подключается первым, активного подключения ещё нет — значит, предзаготовить
  share-ссылку для него нельзя.
- Вместо этого — на каждую "роль" просмотра (candidate / interviewer) создаётся
  СВОЙ отдельный connection (у VNC есть нативный параметр "read-only" для
  интервьюера, поэтому второй connection достаточно создать с этим параметром,
  без зависимости от активной сессии) и СВОЙ scoped-пользователь с READ-правом
  только на этот connection. Проверено: такой пользователь логинится сразу и
  видит ровно один свой connection.
"""

import secrets
import string

import requests


class GuacamoleClient:
    def __init__(
        self,
        base_url: str,
        admin_user: str,
        admin_password: str,
        data_source: str = "postgresql",
        public_base_url: str | None = None,
    ):
        self._base_url = base_url.rstrip("/")
        # URL, доступный из браузера кандидата/интервьюера (НЕ docker-service-name) —
        # тот же приём, что VITE_PANEL_API_URL для PanelUI. Используется только для
        # отображения наружу, сами REST-вызовы всегда идут по base_url.
        self.public_base_url = (public_base_url or base_url).rstrip("/")
        self._admin_user = admin_user
        self._admin_password = admin_password
        self._data_source = data_source
        self._token: str | None = None

    def _api(self, path: str) -> str:
        return f"{self._base_url}/api/session/data/{self._data_source}{path}"

    def _ensure_token(self) -> str:
        if self._token:
            return self._token
        resp = requests.post(
            f"{self._base_url}/api/tokens",
            data={"username": self._admin_user, "password": self._admin_password},
            timeout=10,
        )
        resp.raise_for_status()
        self._token = resp.json()["authToken"]
        return self._token

    def _request(self, method: str, path: str, **kwargs):
        token = self._ensure_token()
        params = kwargs.pop("params", {})
        params["token"] = token
        resp = requests.request(method, self._api(path), params=params, timeout=10, **kwargs)
        if resp.status_code == 403 and self._token:
            # Токен истёк — перелогиниваемся один раз и повторяем запрос.
            self._token = None
            params["token"] = self._ensure_token()
            resp = requests.request(method, self._api(path), params=params, timeout=10, **kwargs)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def create_connection(self, name: str, hostname: str, port: int, read_only: bool = False) -> str:
        parameters = {"hostname": hostname, "port": str(port)}
        if read_only:
            parameters["read-only"] = "true"
        body = {
            "parentIdentifier": "ROOT",
            "name": name,
            "protocol": "vnc",
            "parameters": parameters,
            "attributes": {},
        }
        result = self._request("POST", "/connections", json=body)
        return result["identifier"]

    def delete_connection(self, connection_id: str) -> None:
        self._request("DELETE", f"/connections/{connection_id}")

    @staticmethod
    def _random_password(length: int = 24) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def create_scoped_user(self, username: str, connection_id: str) -> str:
        """Создаёт пользователя с READ-доступом ровно к одному connection, возвращает пароль."""
        password = self._random_password()
        self._request(
            "POST",
            "/users",
            json={
                "username": username,
                "password": password,
                "attributes": {"disabled": "", "expired": ""},
            },
        )
        self._request(
            "PATCH",
            f"/users/{username}/permissions",
            json=[{"op": "add", "path": f"/connectionPermissions/{connection_id}", "value": "READ"}],
        )
        return password

    def delete_user(self, username: str) -> None:
        self._request("DELETE", f"/users/{username}")
