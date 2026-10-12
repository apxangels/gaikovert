"""
VMDriver — абстракция создания/удаления машины сессии (роль arm или target,
см. CLAUDE.md "Целевая платформа"). Два драйвера:

- MockDriver — реально работает, но не создаёт VM. Используется там, где нет
  /dev/kvm (как в этом окружении): возвращает фиктивный handle, указывающий на
  MOCK_VM_HOST, чтобы можно было честно проверить весь путь Constructor →
  Guacamole (создание connection/user), не имея реального гостя за VNC.
- LibvirtDriver — написан по документации libvirt-python как настоящая
  реализация, но НЕ исполнялся и НЕ протестирован в этом сэндбоксе (нет
  /dev/kvm). Перед использованием на реальном хосте нужно подставить реальные
  имена storage pool/network и положить базовые qcow2-образы — см. README.md.
"""

import abc
import os
import time
import uuid

from pydantic import BaseModel


class MachineHandle(BaseModel):
    id: str
    ip: str
    hostname: str | None = None


class VMDriver(abc.ABC):
    @abc.abstractmethod
    def create_machine(
        self, role: str, name: str, cloud_init: str, override: dict | None
    ) -> MachineHandle: ...

    @abc.abstractmethod
    def destroy_machine(self, handle: MachineHandle) -> None: ...


class MockDriver(VMDriver):
    def __init__(self) -> None:
        self._host = os.environ.get("MOCK_VM_HOST", "guacd")

    def create_machine(self, role, name, cloud_init, override) -> MachineHandle:
        return MachineHandle(id=f"mock-{uuid.uuid4()}", ip=self._host, hostname=name)

    def destroy_machine(self, handle: MachineHandle) -> None:
        pass  # нечего удалять, ни одна реальная VM не создавалась


class LibvirtDriver(VMDriver):
    def __init__(self) -> None:
        import libvirt  # пакет нужен только этому драйверу — лениво, чтобы

        # MockDriver не требовал libvirt-python/нативных либ там, где их нет.

        self._libvirt = libvirt
        uri = os.environ.get("LIBVIRT_URI", "qemu:///system")
        self._conn = libvirt.open(uri)
        if self._conn is None:
            raise RuntimeError(f"не удалось подключиться к libvirt по {uri}")
        self._network = os.environ.get("LIBVIRT_NETWORK", "default")
        self._base_image_arm = os.environ.get(
            "LIBVIRT_BASE_IMAGE_ARM", "/var/lib/libvirt/images/base-arm.qcow2"
        )
        self._base_image_target = os.environ.get(
            "LIBVIRT_BASE_IMAGE_TARGET", "/var/lib/libvirt/images/base-target.qcow2"
        )
        self._image_dir = os.environ.get("LIBVIRT_IMAGE_DIR", "/var/lib/libvirt/images")

    def create_machine(self, role: str, name: str, cloud_init: str, override: dict | None) -> MachineHandle:
        import subprocess
        import tempfile

        base_image = self._base_image_arm if role == "arm" else self._base_image_target
        domain_name = f"gaikovert-{name}-{uuid.uuid4().hex[:8]}"
        disk_path = f"{self._image_dir}/{domain_name}.qcow2"

        # 1. Copy-on-write клон базового образа — быстро, не трогает оригинал.
        subprocess.run(
            ["qemu-img", "create", "-f", "qcow2", "-b", base_image, "-F", "qcow2", disk_path],
            check=True,
        )

        # 2. NoCloud seed ISO с cloud-init конфигурацией этой машины.
        with tempfile.TemporaryDirectory() as tmp:
            user_data_path = os.path.join(tmp, "user-data")
            meta_data_path = os.path.join(tmp, "meta-data")
            with open(user_data_path, "w") as f:
                f.write(cloud_init)
            with open(meta_data_path, "w") as f:
                f.write(f"instance-id: {domain_name}\nlocal-hostname: {name}\n")
            seed_path = f"{self._image_dir}/{domain_name}-seed.iso"
            subprocess.run(["cloud-localds", seed_path, user_data_path, meta_data_path], check=True)

        # 3. Домен: один диск + seed ISO + сеть сессии + VNC-граф (для Guacamole).
        domain_xml = f"""
        <domain type='kvm'>
          <name>{domain_name}</name>
          <memory unit='MiB'>2048</memory>
          <vcpu>2</vcpu>
          <os><type arch='x86_64'>hvm</type></os>
          <devices>
            <disk type='file' device='disk'>
              <driver name='qemu' type='qcow2'/>
              <source file='{disk_path}'/>
              <target dev='vda' bus='virtio'/>
            </disk>
            <disk type='file' device='cdrom'>
              <driver name='qemu' type='raw'/>
              <source file='{seed_path}'/>
              <target dev='sda' bus='sata'/>
              <readonly/>
            </disk>
            <interface type='network'>
              <source network='{self._network}'/>
              <model type='virtio'/>
            </interface>
            <graphics type='vnc' autoport='yes' listen='0.0.0.0'/>
          </devices>
        </domain>
        """
        domain = self._conn.defineXML(domain_xml)
        domain.create()

        ip = self._wait_for_ip(domain)
        return MachineHandle(id=domain_name, ip=ip, hostname=name)

    def _wait_for_ip(self, domain, timeout: int = 120) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            ifaces = domain.interfaceAddresses(self._libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE)
            for iface in ifaces.values():
                for addr in iface.get("addrs", []):
                    if addr["type"] == self._libvirt.VIR_IP_ADDR_TYPE_IPV4:
                        return addr["addr"]
            time.sleep(2)
        raise TimeoutError(f"{domain.name()}: не дождались DHCP-адреса за {timeout}с")

    def destroy_machine(self, handle: MachineHandle) -> None:
        try:
            domain = self._conn.lookupByName(handle.id)
            if domain.isActive():
                domain.destroy()
            domain.undefine()
        except self._libvirt.libvirtError:
            pass  # уже остановлен/не существует — для destroy это не ошибка


def get_driver() -> VMDriver:
    driver_name = os.environ.get("VM_DRIVER", "mock")
    if driver_name == "libvirt":
        return LibvirtDriver()
    return MockDriver()
