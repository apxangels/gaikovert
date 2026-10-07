import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import type { ServiceTemplate } from "../types";

export default function ServiceLibraryPage() {
  const [items, setItems] = useState<ServiceTemplate[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [type, setType] = useState("");
  const [configText, setConfigText] = useState("{}");

  async function load() {
    try {
      setItems(await api.listServiceTemplates());
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
      const base_config = configText.trim() ? JSON.parse(configText) : {};
      await api.createServiceTemplate({ name, type, base_config });
      setName("");
      setType("");
      setConfigText("{}");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteServiceTemplate(id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <div>
      <h1>Библиотека сервисов</h1>
      {error && <p className="error">{error}</p>}

      <ul className="library-list">
        {items.map((it) => (
          <li key={it.id}>
            <b>{it.name}</b> <span className="muted">({it.type})</span>
            <pre>{JSON.stringify(it.base_config)}</pre>
            <button onClick={() => handleDelete(it.id)}>удалить</button>
          </li>
        ))}
        {items.length === 0 && <li className="muted">Библиотека пуста.</li>}
      </ul>

      <h2>Новый сервис</h2>
      <form onSubmit={handleCreate}>
        <label>
          Имя
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Тип
          <input
            value={type}
            onChange={(e) => setType(e.target.value)}
            required
            placeholder="nginx, docker, postgres, prometheus..."
          />
        </label>
        <label>
          Базовый конфиг (JSON)
          <textarea value={configText} onChange={(e) => setConfigText(e.target.value)} />
        </label>
        <button className="btn" type="submit">
          Создать
        </button>
      </form>
    </div>
  );
}
