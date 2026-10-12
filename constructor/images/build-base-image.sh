#!/usr/bin/env bash
# Готовит golden qcow2-образ под роль arm/target (см. CLAUDE.md, Constructor →
# "Базовые образы (golden image)"). One-time ручной прогон НА САМОМ libvirt-хосте,
# не часть Panel/Constructor и не выполнялся в этом репозитории (нет /dev/kvm
# в окружении, где это писалось — проверьте каждый шаг перед использованием).
#
# Идея: не ставим ОС из ISO-инсталлятора — берём готовый cloud-образ Oracle
# Linux (уже с cloud-init), один раз ставим в него пакеты нужного каталога
# сервисов, "генерализуем" и сохраняем как base-образ. Сессионный cloud-init
# (из Panel) на этом образе потом только конфигурирует/включает сервисы —
# секунды, а не минуты.
#
# Использование:
#   ./build-base-image.sh arm    /var/lib/libvirt/images/base-arm.qcow2
#   ./build-base-image.sh target /var/lib/libvirt/images/base-target.qcow2
#
# Перед запуском проверьте/поправьте: CLOUD_IMAGE_URL (реальная ссылка на
# Oracle Linux 9U4 cloud image), LIBVIRT_NETWORK, объём диска/памяти.

set -euo pipefail

ROLE="${1:?usage: $0 <arm|target> <output-qcow2-path>}"
OUTPUT_PATH="${2:?usage: $0 <arm|target> <output-qcow2-path>}"

if [[ "$ROLE" != "arm" && "$ROLE" != "target" ]]; then
  echo "ROLE должен быть 'arm' или 'target', получено: $ROLE" >&2
  exit 1
fi

# TODO: подставить реальную ссылку на Oracle Linux 9U4 cloud image
# (см. https://yum.oracle.com/oracle-linux-templates.html) — соответствует
# ISO OracleLinux-R9-U4-x86_64-dvd.iso, лежащему в репозитории.
CLOUD_IMAGE_URL="${CLOUD_IMAGE_URL:?укажите CLOUD_IMAGE_URL на Oracle Linux 9U4 cloud qcow2}"
LIBVIRT_NETWORK="${LIBVIRT_NETWORK:-default}"
WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

WORK_IMAGE="$WORK_DIR/work.qcow2"
DOMAIN_NAME="gaikovert-build-$ROLE-$$"

echo "==> Скачиваю базовый cloud-образ (если ещё не скачан локально)"
CLOUD_IMAGE_CACHE="/var/lib/libvirt/images/_cache_$(basename "$CLOUD_IMAGE_URL")"
if [[ ! -f "$CLOUD_IMAGE_CACHE" ]]; then
  curl -L -o "$CLOUD_IMAGE_CACHE" "$CLOUD_IMAGE_URL"
fi

echo "==> Копирую во временный рабочий образ (увеличиваю диск под пакеты)"
cp "$CLOUD_IMAGE_CACHE" "$WORK_IMAGE"
qemu-img resize "$WORK_IMAGE" 20G

# Пакеты, которые должны быть предустановлены, чтобы cloud-init сессии не
# тянул их из сети каждый раз — см. CLAUDE.md "Библиотека шаблонов" и
# "Целевая платформа" (desktop-утилиты для arm, сервисный стек для target).
case "$ROLE" in
  arm)
    PACKAGES="firefox xterm git curl openssh-clients docker-ce-cli postgresql tcpdump telnet"
    ;;
  target)
    PACKAGES="docker-ce nginx postgresql-server firewalld"
    ;;
esac

echo "==> Генерирую временный cloud-init только для сборки образа (не для сессий)"
cat > "$WORK_DIR/user-data" <<EOF
#cloud-config
package_update: true
packages: [$(echo "$PACKAGES" | sed 's/ /, /g')]
runcmd:
  - [ systemctl, disable, docker ]
  - [ systemctl, disable, nginx ]
  - [ systemctl, disable, firewalld ]
  # Сервисы ставим, но не включаем — включение/конфигурация это задача
  # сессионного cloud-init из Panel (fault/override конкретного сценария).
power_state:
  mode: poweroff
  timeout: 30
  condition: true
EOF
cat > "$WORK_DIR/meta-data" <<EOF
instance-id: $DOMAIN_NAME
local-hostname: $DOMAIN_NAME
EOF
cloud-localds "$WORK_DIR/seed.iso" "$WORK_DIR/user-data" "$WORK_DIR/meta-data"

echo "==> Поднимаю временную VM для установки пакетов"
virt-install \
  --name "$DOMAIN_NAME" \
  --memory 2048 --vcpus 2 \
  --disk path="$WORK_IMAGE",format=qcow2,bus=virtio \
  --disk path="$WORK_DIR/seed.iso",device=cdrom,bus=sata \
  --network network="$LIBVIRT_NETWORK",model=virtio \
  --os-variant centos-stream9 \
  --import \
  --graphics none \
  --noautoconsole

echo "==> Жду завершения cloud-init и выключения VM (package_update/install по сети — минуты)"
echo "    Проверьте вручную при необходимости: virsh console $DOMAIN_NAME"
echo "    или смотрите /var/log/cloud-init-output.log внутри гостя."
for _ in $(seq 1 120); do
  if ! virsh domstate "$DOMAIN_NAME" 2>/dev/null | grep -q running; then
    break
  fi
  sleep 10
done
virsh destroy "$DOMAIN_NAME" 2>/dev/null || true
virsh undefine "$DOMAIN_NAME" 2>/dev/null || true

echo "==> Генерализую образ (machine-id, SSH host keys, cloud-init cache)"
if command -v virt-sysprep >/dev/null; then
  virt-sysprep -a "$WORK_IMAGE" \
    --operations machine-id,ssh-hostkeys,cloud-init,bash-history,logfiles
else
  echo "    virt-sysprep не найден (пакет libguestfs-tools) — генерализация НЕ выполнена." >&2
  echo "    Поставьте libguestfs-tools или сгенерализуйте образ руками перед использованием." >&2
fi

echo "==> Сохраняю итоговый base-образ в $OUTPUT_PATH"
mv "$WORK_IMAGE" "$OUTPUT_PATH"

echo "Готово: $OUTPUT_PATH — укажите этот путь в LIBVIRT_BASE_IMAGE_$(echo "$ROLE" | tr '[:lower:]' '[:upper:]')"
