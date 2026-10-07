// Отражают Pydantic-схемы Panel (panel/schemas.py). id — UUID в виде строки.

export type Role = "arm" | "target";

export interface ServiceTemplate {
  id: string;
  name: string;
  type: string;
  base_config: Record<string, unknown>;
  created_at: string;
}

export interface ServiceTemplateInput {
  name: string;
  type: string;
  base_config: Record<string, unknown>;
}

export interface MachineTemplate {
  id: string;
  name: string;
  role: Role;
  cloud_init: string;
  created_at: string;
}

export interface MachineTemplateInput {
  name: string;
  role: Role;
  cloud_init: string;
}

export interface ScenarioServiceInput {
  service_template_id: string;
  override?: Record<string, unknown> | null;
}

export interface ScenarioServiceOut {
  id: string;
  service_template_id: string;
  service_template_name: string;
  override: Record<string, unknown> | null;
}

export interface ScenarioTargetMachineInput {
  name: string;
  machine_template_id: string;
  machine_override?: Record<string, unknown> | null;
  fault?: Record<string, unknown> | null;
  services: ScenarioServiceInput[];
}

export interface ScenarioTargetMachineOut {
  id: string;
  name: string;
  machine_template_id: string;
  machine_template_name: string;
  machine_override: Record<string, unknown> | null;
  fault: Record<string, unknown> | null;
  services: ScenarioServiceOut[];
}

export interface ScenarioInput {
  slug: string;
  title: string;
  arm_machine_template_id: string;
  arm_override?: Record<string, unknown> | null;
  briefing_root_cause?: string | null;
  briefing_expected_steps: string[];
  target_machines: ScenarioTargetMachineInput[];
}

export interface ScenarioCard {
  id: string;
  slug: string;
  title: string;
  created_at: string;
}

export interface ScenarioDetail {
  id: string;
  slug: string;
  title: string;
  arm_machine_template_id: string;
  arm_machine_template_name: string;
  arm_override: Record<string, unknown> | null;
  briefing_root_cause: string | null;
  briefing_expected_steps: string[];
  target_machines: ScenarioTargetMachineOut[];
  created_at: string;
}

// Заглушка, пока нет Constructor — status всегда "awaiting_constructor",
// spectator_url всегда null. См. CLAUDE.md, Panel п.5/6.
export interface ScenarioSession {
  id: string;
  scenario_id: string;
  status: string;
  spectator_url: string | null;
  created_at: string;
}
