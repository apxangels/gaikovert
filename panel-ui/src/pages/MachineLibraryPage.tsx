import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { MachineTemplate, Role } from "../types";

const ROLES: Role[] = ["arm", "target"];

export default function MachineLibraryPage() {
  const [items, setItems] = useState<MachineTemplate[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [role, setRole] = useState<Role>("target");
  const [cloudInit, setCloudInit] = useState("#cloud-config\n");

  async function load() {
    try {
      setItems(await api.listMachineTemplates());
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.createMachineTemplate({ name, role, cloud_init: cloudInit });
      setName("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteMachineTemplate(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <h1>Библиотека machine-конфигураций</h1>
      {error && <p className="error">{error}</p>}

      {ROLES.map((r) => (
        <div key={r}>
          <h2>{r === "arm" ? "АРМ" : "Target"}</h2>
          <ul className="library-list">
            {items
              .filter((i) => i.role === r)
              .map((it) => (
                <li key={it.id}>
                  <b>{it.name}</b>
                  <pre>{it.cloud_init}</pre>
                  <button onClick={() => handleDelete(it.id)}>удалить</button>
                </li>
              ))}
            {items.filter((i) => i.role === r).length === 0 && (
              <li className="muted">Шаблонов роли {r} пока нет.</li>
            )}
          </ul>
        </div>
      ))}

      <h2>Новая machine-конфигурация</h2>
      <form onSubmit={handleCreate}>
        <label>
          Имя
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Роль
          <select value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
        <label>
          cloud-init
          <textarea value={cloudInit} onChange={(e) => setCloudInit(e.target.value)} rows={6} />
        </label>
        <button className="btn" type="submit">
          Создать
        </button>
      </form>
    </div>
  );
}
