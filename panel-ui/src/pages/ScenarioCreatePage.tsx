import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { MachineTemplate, ScenarioInput, ServiceTemplate } from "../types";

interface EditableService {
  service_template_id: string;
  overrideText: string;
}

interface EditableTargetMachine {
  name: string;
  machine_template_id: string;
  machineOverrideText: string;
  faultText: string;
  services: EditableService[];
}

function emptyService(): EditableService {
  return { service_template_id: "", overrideText: "" };
}

function emptyTargetMachine(): EditableTargetMachine {
  return { name: "", machine_template_id: "", machineOverrideText: "", faultText: "", services: [] };
}

function parseJsonOrNull(text: string, label: string): Record<string, unknown> | null {
  if (!text.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label}: невалидный JSON`);
  }
}

export default function ScenarioCreatePage() {
  const navigate = useNavigate();

  const [armTemplates, setArmTemplates] = useState<MachineTemplate[]>([]);
  const [targetTemplates, setTargetTemplates] = useState<MachineTemplate[]>([]);
  const [serviceTemplates, setServiceTemplates] = useState<ServiceTemplate[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [armTemplateId, setArmTemplateId] = useState("");
  const [rootCause, setRootCause] = useState("");
  const [expectedSteps, setExpectedSteps] = useState(""); // по строке на шаг
  const [targetMachines, setTargetMachines] = useState<EditableTargetMachine[]>([emptyTargetMachine()]);

  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([api.listMachineTemplates("arm"), api.listMachineTemplates("target"), api.listServiceTemplates()])
      .then(([arm, target, services]) => {
        setArmTemplates(arm);
        setTargetTemplates(target);
        setServiceTemplates(services);
        if (arm.length > 0) setArmTemplateId(arm[0].id);
      })
      .catch((e) => setLoadError(String(e)));
  }, []);

  function updateTargetMachine(index: number, patch: Partial<EditableTargetMachine>) {
    setTargetMachines((prev) => prev.map((tm, i) => (i === index ? { ...tm, ...patch } : tm)));
  }

  function addTargetMachine() {
    setTargetMachines((prev) => [...prev, emptyTargetMachine()]);
  }

  function removeTargetMachine(index: number) {
    setTargetMachines((prev) => prev.filter((_, i) => i !== index));
  }

  function addService(tmIndex: number) {
    setTargetMachines((prev) =>
      prev.map((tm, i) => (i === tmIndex ? { ...tm, services: [...tm.services, emptyService()] } : tm))
    );
  }

  function updateService(tmIndex: number, svcIndex: number, patch: Partial<EditableService>) {
    setTargetMachines((prev) =>
      prev.map((tm, i) =>
        i === tmIndex
          ? { ...tm, services: tm.services.map((s, j) => (j === svcIndex ? { ...s, ...patch } : s)) }
          : tm
      )
    );
  }

  function removeService(tmIndex: number, svcIndex: number) {
    setTargetMachines((prev) =>
      prev.map((tm, i) => (i === tmIndex ? { ...tm, services: tm.services.filter((_, j) => j !== svcIndex) } : tm))
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    try {
      const payload: ScenarioInput = {
        slug,
        title,
        arm_machine_template_id: armTemplateId,
        arm_override: null,
        briefing_root_cause: rootCause || null,
        briefing_expected_steps: expectedSteps
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        target_machines: targetMachines.map((tm) => ({
          name: tm.name,
          machine_template_id: tm.machine_template_id,
          machine_override: parseJsonOrNull(tm.machineOverrideText, `Machine override (${tm.name || "?"})`),
          fault: parseJsonOrNull(tm.faultText, `Fault (${tm.name || "?"})`),
          services: tm.services.map((s) => ({
            service_template_id: s.service_template_id,
            override: parseJsonOrNull(s.overrideText, "Service override"),
          })),
        })),
      };

      setSubmitting(true);
      const created = await api.createScenario(payload);
      navigate(`/scenarios/${created.id}`);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (loadError) return <p className="error">{loadError}</p>;

  return (
    <form onSubmit={handleSubmit} className="scenario-form">
      <h1>Новый сценарий</h1>

      <label>
        Slug
        <input value={slug} onChange={(e) => setSlug(e.target.value)} required />
      </label>
      <label>
        Название
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
      </label>
      <label>
        АРМ-шаблон
        <select value={armTemplateId} onChange={(e) => setArmTemplateId(e.target.value)} required>
          <option value="" disabled>
            — выбрать —
          </option>
          {armTemplates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </label>

      <h2>Target-машины</h2>
      {targetMachines.map((tm, tmIndex) => (
        <fieldset key={tmIndex} className="target-machine-form">
          <legend>
            Машина {tmIndex + 1}{" "}
            {targetMachines.length > 1 && (
              <button type="button" onClick={() => removeTargetMachine(tmIndex)}>
                убрать
              </button>
            )}
          </legend>

          <label>
            Имя
            <input
              value={tm.name}
              onChange={(e) => updateTargetMachine(tmIndex, { name: e.target.value })}
              required
            />
          </label>
          <label>
            Machine-шаблон (target)
            <select
              value={tm.machine_template_id}
              onChange={(e) => updateTargetMachine(tmIndex, { machine_template_id: e.target.value })}
              required
            >
              <option value="" disabled>
                — выбрать —
              </option>
              {targetTemplates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Machine override (JSON, опционально)
            <textarea
              value={tm.machineOverrideText}
              onChange={(e) => updateTargetMachine(tmIndex, { machineOverrideText: e.target.value })}
              placeholder="{}"
            />
          </label>
          <label>
            Fault (JSON)
            <textarea
              value={tm.faultText}
              onChange={(e) => updateTargetMachine(tmIndex, { faultText: e.target.value })}
              placeholder='{"type": "firewalld-block-port", "params": {"port": 8080}}'
            />
          </label>

          <h3>Сервисы</h3>
          {tm.services.map((svc, svcIndex) => (
            <div key={svcIndex} className="service-form">
              <select
                value={svc.service_template_id}
                onChange={(e) => updateService(tmIndex, svcIndex, { service_template_id: e.target.value })}
                required
              >
                <option value="" disabled>
                  — выбрать сервис —
                </option>
                {serviceTemplates.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <textarea
                value={svc.overrideText}
                onChange={(e) => updateService(tmIndex, svcIndex, { overrideText: e.target.value })}
                placeholder="override JSON, опционально"
              />
              <button type="button" onClick={() => removeService(tmIndex, svcIndex)}>
                убрать сервис
              </button>
            </div>
          ))}
          <button type="button" onClick={() => addService(tmIndex)}>
            + сервис
          </button>
        </fieldset>
      ))}
      <button type="button" onClick={addTargetMachine}>
        + target-машина
      </button>

      <h2>Бриф для интервьюера</h2>
      <label>
        Root cause
        <input value={rootCause} onChange={(e) => setRootCause(e.target.value)} />
      </label>
      <label>
        Ожидаемые шаги (по одному на строку)
        <textarea value={expectedSteps} onChange={(e) => setExpectedSteps(e.target.value)} />
      </label>

      {submitError && <p className="error">{submitError}</p>}
      <button className="btn" type="submit" disabled={submitting}>
        {submitting ? "Сохраняю…" : "Сохранить сценарий"}
      </button>
    </form>
  );
}
