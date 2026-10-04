export type StepStatus = 'pending' | 'active' | 'done' | 'error' | 'skipped'
export type PlanState = 'running' | 'needs_input' | 'error' | 'done'
export type PlanStep = { title: string; status: StepStatus }
export type PlanStage = { name: string; steps: PlanStep[] }
export type AgentRun = {
  id: string
  title: string
  state: 'running' | 'waiting' | 'done' | 'error'
  tool: string
  startedAt: number
  endedAt: number | null
}
export type Plan = {
  id: string
  title: string
  stages: PlanStage[]
  state: PlanState
  note: string | null
  startedAt: number
  doneAt: number | null
  agents: AgentRun[]
}
export type TitleState = { last: string | null; isUserOwned: boolean }

declare module 'claude-code' {
  interface PluginState {
    progress: { plans: Plan[]; isOpen: boolean; tick: number; title: TitleState }
  }
}
