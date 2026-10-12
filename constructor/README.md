# Constructor

Backend-сервис Constructor (см. корневой `CLAUDE.md`). Принимает от Panel готовую
конфигурацию сессии (АРМ + target-машины, каждая — уже готовый cloud-init),
создаёт машины через `VMDriver` и регистрирует доступ к ним в Guacamole через
`GuacamoleClient`.

## VMDriver

- `mock` (по умолчанию, `VM_DRIVER=mock`) — реально работает, но не создаёт VM.
  Возвращает фиктивный handle, указывающий на `MOCK_VM_HOST` (по умолчанию —
  `guacd`), чтобы можно было честно проверить весь путь Constructor → Guacamole
  (создание connection/scoped-user), не имея реального гостя за VNC.
- `libvirt` (`VM_DRIVER=libvirt`) — настоящая реализация на libvirt-python.
  **Не исполнялась и не тестировалась** в этом окружении (нет `/dev/kvm`).
  Перед использованием на реальном хосте:
  - `pip install libvirt-python` в образ (версия должна быть близка к версии
    установленного libvirt на хосте — поэтому не зафиксирована в
    `requirements.txt` жёстко);
  - подготовить базовые qcow2-образы под роли arm/target (golden image — см.
    `images/build-base-image.sh` и корневой `CLAUDE.md`, "Базовые образы") и
    указать пути через `LIBVIRT_BASE_IMAGE_ARM` / `LIBVIRT_BASE_IMAGE_TARGET`;
  - проверить, что `LIBVIRT_NETWORK` (по умолчанию `default`) существует в
    `virsh net-list`;
  - на хосте должен быть установлен `cloud-localds` (пакет `cloud-image-utils`
    на Debian/Ubuntu) для генерации seed ISO с cloud-init.

## GuacamoleClient

Механика **проверена вручную** на реальном Guacamole 1.5.5 (см. `docker-compose.yml`:
`guacamole` + `guacd` + `guacamole-db`) до того, как это было написано:

- Sharing profiles (готовые share-ссылки) не годятся — Guacamole выдаёт
  share-ссылку только для уже активного (кем-то открытого) подключения, а
  кандидат подключается первым.
- Вместо этого на каждую роль просмотра (candidate/interviewer) — отдельный
  connection (у VNC есть нативный параметр `read-only`, поэтому interviewer —
  это просто второй connection с этим параметром) + отдельный scoped-пользователь
  с READ-правом ровно на свой connection. Такой пользователь логинится сразу,
  без дополнительных шагов, и видит только свой connection — проверено.

## API

- `POST /sessions` — тело: `{session_id, arm_machine, target_machines[]}` (см.
  `server.py:SessionCreateRequest`). Создаёт машины, регистрирует два
  connection+user в Guacamole, возвращает креды кандидата и интервьюера.
- `GET /sessions/{id}` — список созданных машин/connection'ов (для отладки).
- `DELETE /sessions/{id}` — удаляет connection'ы, пользователей в Guacamole и
  машины через VMDriver.

Состояние сессий — **in-memory**, не переживает перезапуск Constructor
(осознанное ограничение MVP, см. корневой `CLAUDE.md`).

## Что дальше (не входит в эту итерацию)

- Panel должна вызывать `POST /sessions` при запуске сценария и хранить
  `candidate`/`interviewer` креды у себя (PIN в Panel маппится на candidate-креды).
- Front должен уметь по PIN получить креды и залогиниться в Guacamole (POST
  `/api/tokens`, затем открыть `#/client/...` с полученным authToken) —
  механика самого auto-login во View без формы логина Guacamole не
  проверялась живым браузером в этой сессии, проверить при реализации Front.
