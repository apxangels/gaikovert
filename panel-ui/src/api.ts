import type {
  MachineTemplate,
  MachineTemplateInput,
  Role,
  ScenarioCard,
  ScenarioDetail,
  ScenarioInput,
  ScenarioSession,
  ServiceTemplate,
  ServiceTemplateInput,
} from "./types";

// В браузере недоступен docker-network — URL должен быть тем, по которому
// Panel видна с хоста (см. .env.example / VITE_PANEL_API_URL).
const BASE_URL = import.meta.env.VITE_PANEL_API_URL ?? "http://localhost:8001";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${options?.method ?? "GET"} ${path} → ${res.status}${body ? `: ${body}` : ""}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return (await res.json()) as T;
}

export const api = {
  // Библиотека сервисов
  listServiceTemplates: () => request<ServiceTemplate[]>("/service-templates"),
  createServiceTemplate: (payload: ServiceTemplateInput) =>
    request<ServiceTemplate>("/service-templates", { method: "POST", body: JSON.stringify(payload) }),
  deleteServiceTemplate: (id: string) => request<void>(`/service-templates/${id}`, { method: "DELETE" }),

  // Библиотека machine-конфигураций
  listMachineTemplates: (role?: Role) =>
    request<MachineTemplate[]>(`/machine-templates${role ? `?role=${role}` : ""}`),
  createMachineTemplate: (payload: MachineTemplateInput) =>
    request<MachineTemplate>("/machine-templates", { method: "POST", body: JSON.stringify(payload) }),
  deleteMachineTemplate: (id: string) => request<void>(`/machine-templates/${id}`, { method: "DELETE" }),

  // Сценарии
  listScenarios: () => request<ScenarioCard[]>("/scenarios"),
  getScenario: (id: string) => request<ScenarioDetail>(`/scenarios/${id}`),
  createScenario: (payload: ScenarioInput) =>
    request<ScenarioDetail>("/scenarios", { method: "POST", body: JSON.stringify(payload) }),
  deleteScenario: (id: string) => request<void>(`/scenarios/${id}`, { method: "DELETE" }),

  // Сессии (заглушка, ждёт Constructor)
  launchScenario: (scenarioId: string) =>
    request<ScenarioSession>(`/scenarios/${scenarioId}/sessions`, { method: "POST" }),
  listScenarioSessions: (scenarioId: string) =>
    request<ScenarioSession[]>(`/scenarios/${scenarioId}/sessions`),
};
