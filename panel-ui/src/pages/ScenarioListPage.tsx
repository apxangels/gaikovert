import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { ScenarioCard } from "../types";

export default function ScenarioListPage() {
  const [scenarios, setScenarios] = useState<ScenarioCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listScenarios()
      .then(setScenarios)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Сценарии</h1>
        <Link className="btn" to="/scenarios/new">
          + Новый сценарий
        </Link>
      </div>

      {error && <p className="error">{error}</p>}
      {!scenarios && !error && <p>Загрузка…</p>}
      {scenarios && scenarios.length === 0 && <p className="muted">Сценариев пока нет.</p>}

      <div className="card-grid">
        {scenarios?.map((s) => (
          <Link key={s.id} to={`/scenarios/${s.id}`} className="card">
            <h3>{s.title}</h3>
            <code>{s.slug}</code>
          </Link>
        ))}
      </div>
    </div>
  );
}
