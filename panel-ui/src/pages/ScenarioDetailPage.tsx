import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import type { ScenarioDetail, ScenarioSession } from "../types";

export default function ScenarioDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
  const [sessions, setSessions] = useState<ScenarioSession[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    try {
      const [sc, ss] = await Promise.all([api.getScenario(id), api.listScenarioSessions(id)]);
      setScenario(sc);
      setSessions(ss);
    } catch (e) {
      setError(String(e));
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleLaunch() {
    if (!id) return;
    setLaunching(true);
    try {
      await api.launchScenario(id);
      await load();
    } catch (e) {
      setError(String(e));
    } finally {
      setLaunching(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!scenario) return <p>Загрузка…</p>;

  return (
    <div>
      <h1>{scenario.title}</h1>
      <p>
        <code>{scenario.slug}</code>
      </p>

      <section>
        <h2>АРМ</h2>
        <p>Шаблон: {scenario.arm_machine_template_name}</p>
        {scenario.arm_override && <pre>{JSON.stringify(scenario.arm_override, null, 2)}</pre>}
      </section>

      <section>
        <h2>Target-машины</h2>
        {scenario.target_machines.map((tm) => (
          <div key={tm.id} className="library-list" style={{ marginBottom: "1rem" }}>
            <h3>
              {tm.name} <span className="muted">({tm.machine_template_name})</span>
            </h3>
            {tm.fault && (
              <p>
                Fault: <code>{JSON.stringify(tm.fault)}</code>
              </p>
            )}
            {tm.machine_override && (
              <p>
                Machine override: <code>{JSON.stringify(tm.machine_override)}</code>
              </p>
            )}
            <ul>
              {tm.services.map((svc) => (
                <li key={svc.id}>
                  {svc.service_template_name}
                  {svc.override && <code> {JSON.stringify(svc.override)}</code>}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      <section>
        <h2>Бриф для интервьюера</h2>
        <p>{scenario.briefing_root_cause ?? <span className="muted">не указан</span>}</p>
        {scenario.briefing_expected_steps.length > 0 && (
          <ol>
            {scenario.briefing_expected_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        )}
      </section>

      <section>
        <h2>Запуск</h2>
        <button className="btn" onClick={handleLaunch} disabled={launching}>
          {launching ? "Запускаю…" : "Запустить сценарий"}
        </button>
        <ul className="sessions">
          {sessions.map((s) => (
            <li key={s.id}>
              {new Date(s.created_at).toLocaleString()} — <b>{s.status}</b>
              {s.spectator_url ? (
                <>
                  {" "}
                  <a href={s.spectator_url} target="_blank" rel="noreferrer">
                    наблюдать
                  </a>
                </>
              ) : (
                <span className="muted"> — live-наблюдение ждёт подключения Constructor</span>
              )}
            </li>
          ))}
          {sessions.length === 0 && <li className="muted">Запусков пока не было.</li>}
        </ul>
      </section>
    </div>
  );
}
