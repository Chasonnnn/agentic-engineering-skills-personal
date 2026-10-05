export type StepStatus = 'pending' | 'active' | 'done' | 'error' | 'skipped'
export type PlanState = 'running' | 'needs_input' | 'paused' | 'error' | 'done'
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
  // set when the main turn ends with the bar unfinished; cleared on the next update
  pausedAt?: number | null
  // time spent paused, left out of the elapsed time
  pausedMs?: number
  // set on the next prompt after the bar is done; the bar fades out from here
  fadeAt?: number | null
  agents: AgentRun[]
}
export type TitleState = { last: string | null; isUserOwned: boolean; hasAsked: boolean }

declare module 'claude-code' {
  interface PluginState {
    progress: { plans: Plan[]; isOpen: boolean; tick: number; title: TitleState }
  }
}
