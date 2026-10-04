import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AgentRun, Plan, PlanStage, PlanState, StepStatus, TitleState } from '../types'

const TOOL = 'mcp__progress__track'
const plans = atom({ plugin: 'progress', key: 'plans' } as const, [])
const isOpen = atom({ plugin: 'progress', key: 'isOpen' } as const, true)
const tick = atom({ plugin: 'progress', key: 'tick' } as const, 0)
const titleState = atom({ plugin: 'progress', key: 'title' } as const, { last: null, isUserOwned: false } as TitleState)

const MAX_BARS = 3
const DONE_LINGER_MS = 8000
const FADE_MS = 1500 // the last part of the linger, spent fading out
const FADE_FRAMES = 10
const STRIP_LINGER_MS = 5000
const MAX_STRIPS = 4
const AGENTS = 'agents:auto' // slug() never yields ':', so no model id can take it
const PX_PER_COL = 8 // desktop reports about 8 CSS px per column

const STAGE_COLORS = ['#8B7CF6', '#3BA7D9', '#2FB59A', '#E0A33A', '#D96BA6', '#5B8DEF', '#8BBF3C']
const STATE_COLOR: Record<PlanState, string> = { running: '#8B7CF6', needs_input: '#E0A33A', error: '#E5484D', done: '#30A46C' }
const STATE_GLYPH: Record<PlanState, string> = { running: '●', needs_input: '?', error: '!', done: '✓' }
const AGENT_COLOR: Record<AgentRun['state'], string> = { running: '#8B7CF6', waiting: '#E0A33A', done: '#30A46C', error: '#E5484D' }
const STATUSES: StepStatus[] = ['pending', 'active', 'done', 'error', 'skipped']
const stageColor = (i: number) => STAGE_COLORS[i % STAGE_COLORS.length] ?? '#8B7CF6'

const RULES = `# Progress bars
Tasks needing more than ~3 edits or commands get a bar via ${TOOL}: create it once with a title and the full breakdown (2-7 stages with short steps, or one stage for a flat list; titles of at most 4 words, in the user's language), then update it with short calls only: {id, next:true} when the active step is finished, or {id, done:[...], active:"..."}, {id, failed:"...", note}. Send state "needs_input" with a note before asking the user to decide. The bar title also becomes the session name, so make it describe the task. Never describe the bars to the user.`

type Raw = Record<string, unknown>
const str = (v: unknown, max = 120) => (typeof v === 'string' ? v.replace(/\s+/g, ' ').trim().slice(0, max) : '')
const status = (v: unknown): StepStatus => (STATUSES.includes(v as StepStatus) ? (v as StepStatus) : 'pending')
const list = (v: unknown): Raw[] => (Array.isArray(v) ? v.filter(x => x && typeof x === 'object') : []) as Raw[]
const isFinished = (s: StepStatus) => s === 'done' || s === 'skipped'
const same = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase()
const slug = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 40) || 'plan'

// ---------- plan model ----------

// short updates against the stored plan: {next:true}, {done:[titles]}, {active:title}, {failed:title}
function applyOps(stages: PlanStage[], input: Raw): PlanStage[] {
  const out = stages.map(s => ({ ...s, steps: s.steps.map(st => ({ ...st })) }))
  const steps = out.flatMap(s => s.steps)
  const find = (title: string) => steps.find(st => same(st.title, title))
  if (input.next === true) {
    const activeAt = steps.findIndex(st => st.status === 'active')
    const at = activeAt >= 0 ? activeAt : steps.findIndex(st => !isFinished(st.status))
    const cur = steps[at]
    if (cur) cur.status = 'done'
    const following = steps.slice(at + 1).find(st => st.status === 'pending')
    if (following) following.status = 'active'
  }
  for (const t of Array.isArray(input.done) ? input.done : []) {
    const st = typeof t === 'string' ? find(t) : undefined
    if (st) st.status = 'done'
  }
  const active = typeof input.active === 'string' ? find(input.active) : undefined
  if (active) {
    const at = steps.indexOf(active)
    steps.forEach((st, i) => {
      if (st.status === 'active' && i !== at) st.status = i < at ? 'done' : 'pending'
    })
    active.status = 'active'
  }
  const failed = typeof input.failed === 'string' ? find(input.failed) : undefined
  if (failed) failed.status = 'error'

  return out
}

function normalize(input: Raw, prev: Plan | null, now: number, id: string): Plan {
  const isPartial = list(input.stages).length === 0 && prev !== null
  const stages: PlanStage[] = isPartial
    ? applyOps(prev.stages, input)
    : list(input.stages)
        .map(s => ({
          name: str(s.name, 60) || 'Stage',
          steps: list(s.steps).map(st => ({ title: str(st.title) || 'Step', status: status(st.status) })),
        }))
        .filter(s => s.steps.length > 0)
  const steps = stages.flatMap(s => s.steps)
  // a fresh plan with nothing active starts on its first open step
  if (!isPartial && !steps.some(s => s.status === 'active')) {
    const first = steps.find(s => !isFinished(s.status) && s.status !== 'error')
    if (first) first.status = 'active'
  }
  const title = str(input.title, 60) || prev?.title || 'Plan'
  const isAllDone = steps.length > 0 && steps.every(s => isFinished(s.status))
  const asked = input.state as PlanState
  const state: PlanState = STATE_GLYPH[asked] ? asked : isAllDone ? 'done' : typeof input.failed === 'string' ? 'error' : 'running'

  return {
    id,
    title,
    stages,
    state,
    note: str(input.note, 160) || null,
    startedAt: prev?.startedAt ?? now,
    doneAt: state === 'done' ? (prev?.doneAt ?? now) : null,
    agents: prev?.agents ?? [],
  }
}

type Where = { finished: number; total: number; stage: number; step: number; stageSize: number; activeTitle: string | null }

function where(p: Plan): Where {
  const flat = p.stages.flatMap((s, i) => s.steps.map((step, j) => ({ i, j, step })))
  const finished = flat.filter(x => isFinished(x.step.status)).length
  const cur = flat.find(x => x.step.status === 'active') ?? flat.find(x => !isFinished(x.step.status))
  const stage = cur?.i ?? Math.max(0, p.stages.length - 1)
  const stageSize = p.stages[stage]?.steps.length ?? 0

  return { finished, total: flat.length, stage, step: cur ? cur.j + 1 : stageSize, stageSize, activeTitle: cur?.step.title ?? null }
}

const percent = (p: Plan) => {
  const w = where(p)
  return p.state === 'done' ? 100 : Math.round((w.finished / Math.max(1, w.total)) * 100)
}

const duration = (ms: number) => {
  const sec = Math.max(0, Math.round(ms / 1000))
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m${String(sec % 60).padStart(2, '0')}s`
  return `${Math.floor(min / 60)}h${String(min % 60).padStart(2, '0')}m`
}

// 0 until the fade starts, 1 when the bar leaves
const fadeOf = (p: Plan, now: number) =>
  p.doneAt === null ? 0 : Math.min(1, Math.max(0, (now - p.doneAt - (DONE_LINGER_MS - FADE_MS)) / FADE_MS))

// terminal fade: characters drop out in a scattered order as f goes 0 -> 1
const scatter = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453
  return x - Math.floor(x)
}
const dissolve = (text: string, f: number) => (f <= 0 ? text : [...text].map((c, i) => (scatter(i) < f ? ' ' : c)).join(''))

// elapsed time, plus an ETA from the average pace of finished steps
function timing(p: Plan, now: number): string {
  const elapsed = (p.doneAt ?? now) - p.startedAt
  const w = where(p)
  const left = w.total - w.finished
  if (w.finished === 0 || left === 0 || p.state === 'done') return duration(elapsed)
  return `${duration(elapsed)} · ~${duration((elapsed / w.finished) * left)} left`
}

const stageLabel = (p: Plan) => {
  const w = where(p)
  return `${p.stages[w.stage]?.name ?? ''} ${w.step}/${w.stageSize}`
}

const isOpenPlan = (p: Plan) => p.id !== AGENTS && p.state !== 'done'

// ---------- drawing ----------

const esc = (s: string) => s.replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c] ?? c)
const TRACK_H = 14
const STEP_GAP = 1.5
const STAGE_GAP = 5

// where the lit part ended at the last draw, so a redraw glides from there; equal values keep the svg string stable
const lastFill = new Map<string, number>()

// segmented track: one rounded cell per step, stages split by wider gaps and tinted in their own colour;
// the active step shimmers, finished steps light up behind a clip that glides to its new edge
function trackSvg(p: Plan, W: number): string {
  const total = p.stages.reduce((n, s) => n + s.steps.length, 0)
  const gaps = (p.stages.length - 1) * STAGE_GAP + (total - p.stages.length) * STEP_GAP
  const unit = Math.max(2, (W - gaps) / Math.max(1, total))
  const isWaiting = p.state === 'needs_input'
  let x = 0
  let fillTo = 0
  let base = ''
  let lit = ''
  let live = ''
  p.stages.forEach((s, i) => {
    const c = stageColor(i)
    s.steps.forEach((st, j) => {
      const r = `x="${x.toFixed(1)}" y="0" width="${unit.toFixed(1)}" height="${TRACK_H}" rx="3"`
      base += `<rect ${r} fill="#808080" fill-opacity=".16"/>`
      if (isFinished(st.status)) {
        lit += `<rect ${r} fill="${c}" fill-opacity="${st.status === 'skipped' ? '.35' : '.92'}"/>`
        fillTo = x + unit
      } else if (st.status === 'error') {
        base += `<rect ${r} fill="${STATE_COLOR.error}"/>`
      } else if (st.status === 'active') {
        live += isWaiting
          ? `<rect ${r} fill="${STATE_COLOR.needs_input}" fill-opacity=".6"><animate attributeName="fill-opacity" values=".25;.75;.25" dur="1.6s" repeatCount="indefinite"/></rect>`
          : `<rect ${r} fill="${c}" fill-opacity=".38"/><rect ${r} fill="url(#shine)"/>`
      }
      x += unit + (j < s.steps.length - 1 ? STEP_GAP : STAGE_GAP)
    })
  })
  const from = lastFill.get(p.id) ?? fillTo
  lastFill.set(p.id, fillTo)
  const glide =
    Math.abs(from - fillTo) > 0.5
      ? `<animate attributeName="width" from="${from.toFixed(1)}" to="${fillTo.toFixed(1)}" dur=".5s" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1" fill="freeze"/>`
      : ''

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${TRACK_H}" viewBox="0 0 ${W} ${TRACK_H}">
<defs><linearGradient id="shine" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/><animateTransform attributeName="gradientTransform" type="translate" from="-1 0" to="1 0" dur="1.8s" repeatCount="indefinite"/></linearGradient>
<clipPath id="lit"><rect width="${fillTo.toFixed(1)}" height="${TRACK_H}">${glide}</rect></clipPath></defs>
${base}<g clip-path="url(#lit)">${lit}</g>${live}</svg>`
}

// desktop summary line: drawn once per finish, fading and sliding out on its own clock
const summaryCache = new Map<string, string>()
function summarySvg(p: Plan, label: string, W: number, now: number): string {
  const key = `${p.id}:${p.doneAt}:${W}`
  const hit = summaryCache.get(key)
  if (hit) return hit
  const begin = Math.max(0, DONE_LINGER_MS - FADE_MS - (now - (p.doneAt ?? now))) / 1000
  const dur = FADE_MS / 1000
  const ease = 'calcMode="spline" keyTimes="0;1" keySplines=".4 0 .6 1"'
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="16" viewBox="0 0 ${W} 16">
<style>.s{font:400 12.5px 'Anthropic Sans',ui-sans-serif,system-ui,-apple-system,'Segoe UI',sans-serif}</style>
<g><animate attributeName="opacity" from="1" to="0" begin="${begin}s" dur="${dur}s" ${ease} fill="freeze"/>
<animateTransform attributeName="transform" type="translate" from="0 0" to="10 0" begin="${begin}s" dur="${dur}s" ${ease} fill="freeze"/>
<text x="1" y="12" class="s" fill="${STATE_COLOR.done}">✓</text><text x="17" y="12" class="s" fill="#8F8D88">${esc(label)}</text></g></svg>`
  summaryCache.set(key, svg)
  return svg
}

type Seg = { text: string; color?: string; dim?: boolean }

// the terminal's track: block characters per step, a space between stages; the active step's highlight walks with the tick
function trackText(p: Plan, cols: number, n: number): Seg[] {
  const total = p.stages.reduce((k, s) => k + s.steps.length, 0)
  const cells = Math.max(1, Math.floor((cols - (p.stages.length - 1)) / Math.max(1, total)))
  const segs: Seg[] = []
  p.stages.forEach((s, i) => {
    if (i > 0) segs.push({ text: ' ' })
    const c = stageColor(i)
    for (const st of s.steps) {
      if (st.status === 'done') segs.push({ text: '█'.repeat(cells), color: c })
      else if (st.status === 'skipped') segs.push({ text: '▒'.repeat(cells), color: c, dim: true })
      else if (st.status === 'error') segs.push({ text: '█'.repeat(cells), color: STATE_COLOR.error })
      else if (st.status === 'active') {
        const hot = n % cells
        const cl = p.state === 'needs_input' ? STATE_COLOR.needs_input : c
        segs.push({ text: '▒'.repeat(hot), color: cl }, { text: '▓', color: cl }, { text: '▒'.repeat(cells - hot - 1), color: cl })
      } else segs.push({ text: '░'.repeat(cells), dim: true })
    }
  })
  return segs
}

// strips that show: unfinished first, finished ones fold after a few seconds, failed ones stay
function visibleAgents(p: Plan, now: number): { shown: AgentRun[]; hidden: number } {
  const live = p.agents.filter(a => a.state !== 'done' || now - (a.endedAt ?? now) < STRIP_LINGER_MS)
  const ranked = [...live].sort((a, b) => Number(a.state === 'done') - Number(b.state === 'done'))
  return { shown: ranked.slice(0, MAX_STRIPS), hidden: Math.max(0, ranked.length - MAX_STRIPS) }
}

// ---------- engine glue ----------

// adds or replaces one bar by id, keeping at most MAX_BARS and dropping finished ones first;
// computed inside update() from the latest list, so parallel writers do not drop each other
function placeBar(all: readonly Plan[], next: Plan): Plan[] {
  const rest = all.some(p => p.id === next.id) ? all.map(p => (p.id === next.id ? next : p)) : [...all, next]
  while (rest.length > MAX_BARS) {
    const doneAt = rest.findIndex(p => p.state === 'done')
    rest.splice(doneAt >= 0 ? doneAt : 0, 1)
  }
  return rest
}

async function syncStatus($: EngineInterface) {
  const live = (await read($, plans)).filter(isOpenPlan).at(-1)
  if (!live || (await read($, isOpen))) return $.ui.status(undefined)
  const w = where(live)
  $.ui.status(`${live.title} · ${stageLabel(live)}${w.activeTitle ? ` · ${w.activeTitle}` : ''}`)
}

async function dropPlan($: EngineInterface, id: string) {
  lastFill.delete(id)
  for (const k of summaryCache.keys()) if (k.startsWith(`${id}:`)) summaryCache.delete(k)
  await update($, plans, all => all.filter(p => p.id !== id))
  await syncStatus($)
}

// a bar that turns done collapses to a summary line, then leaves
function lingerThenDrop($: EngineInterface, id: string, doneAt: number) {
  // the terminal has no opacity: redraw a few frames while the fade runs
  for (let k = 1; k < FADE_FRAMES; k++) {
    $.clock.after(DONE_LINGER_MS - FADE_MS + (k * FADE_MS) / FADE_FRAMES, () => update($, tick, n => n + 1))
  }
  $.clock.after(DONE_LINGER_MS, async () => {
    const p = (await read($, plans)).find(x => x.id === id)
    if (p?.state === 'done' && p.doneAt === doneAt) await dropPlan($, id)
  })
}

async function putPlan($: EngineInterface, next: Plan) {
  let prev: Plan | undefined
  await update($, plans, all => {
    prev = all.find(p => p.id === next.id)
    return placeBar(all, next)
  })
  if (next.state === 'done' && prev?.state !== 'done' && next.doneAt !== null) lingerThenDrop($, next.id, next.doneAt)
  if (!prev && next.id !== AGENTS) await update($, isOpen, () => true)
  await syncStatus($)
}

// a tiny plan for /bars-demo
const DEMO = (now: number): Plan => {
  const s = (title: string, st: StepStatus) => ({ title, status: st })
  return {
    id: 'demo',
    title: 'Orders module',
    state: 'running',
    note: null,
    startedAt: now - 252_000,
    doneAt: null,
    agents: [
      { id: 'demo-a', title: 'Explore schema', state: 'running', tool: 'Grep', startedAt: now - 41_000, endedAt: null },
      { id: 'demo-b', title: 'Check migrations', state: 'done', tool: 'Done', startedAt: now - 80_000, endedAt: now - 1_000 },
    ],
    stages: [
      { name: 'Analysis', steps: [s('Read modules', 'done'), s('Find dependencies', 'done'), s('List changes', 'done')] },
      { name: 'Migration', steps: [s('Schema', 'done'), s('Migration', 'done'), s('Move data', 'active'), s('Indexes', 'pending')] },
      { name: 'API', steps: [s('Endpoints', 'pending'), s('Validation', 'pending')] },
      { name: 'Verify', steps: [s('Tests', 'pending'), s('Build', 'pending')] },
    ],
  }
}

// ---------- agents: drawn from engine events alone, no model calls ----------
// module maps: a reload forgets running agents, whose strips then stay until the bar closes
const agentHome = new Map<string, string>() // agentId -> bar id
const toolUses = new Map<string, string>() // tool_use_id -> agentId, to find who waits on a permission

async function editAgent($: EngineInterface, agentId: string, change: (a: AgentRun) => AgentRun) {
  const home = agentHome.get(agentId)
  if (!home) return
  const now = await $.clock.now()
  let finished: Plan | null = null
  await update($, plans, all =>
    all.map(p => {
      if (p.id !== home) return p
      const agents = p.agents.map(a => (a.id === agentId ? change(a) : a))
      if (p.id !== AGENTS) return { ...p, agents }
      // the mod's own bar is done once every agent on it has ended
      const isOver = agents.every(a => a.state === 'done' || a.state === 'error')
      const next: Plan = { ...p, agents, state: isOver ? (agents.some(a => a.state === 'error') ? 'error' : 'done') : 'running', doneAt: isOver ? now : null }
      if (next.state === 'done') finished = next
      return next
    }),
  )
  const done = finished as Plan | null
  if (done?.doneAt) lingerThenDrop($, done.id, done.doneAt)
}

const STEP_SCHEMA = { type: 'object', required: ['title', 'status'], properties: { title: { type: 'string' }, status: { enum: STATUSES } } }
const WORK_TOOLS = new Set(['Edit', 'Write', 'MultiEdit', 'NotebookEdit', 'Bash'])
const WORK_BEFORE_NUDGE = 4
const CALLS_BEFORE_STALE = 6
const TITLE_PROMPT = 'Name this work session in 3 to 5 words, Title Case, no quotes or trailing punctuation. Reply with the name only.\n\n<request>\n'

export const register: Register = on => {
  // per-turn counts; a reload only restarts them
  let workCalls = 0
  let sinceUpdate = 0
  let isTouched = false
  let isNudged = false

  on('session.start', async ($, e, next) => {
    await $.tool.register({
      name: 'track',
      description: 'Live progress bar above the prompt, one per id. Create with title + stages; update with short ops (next, done, active, failed) or state.',
      inputSchema: {
        type: 'object',
        required: ['id'],
        properties: {
          id: { type: 'string', description: 'Bar id; reuse it for updates' },
          title: { type: 'string', description: 'At most 4 words; also used as the session name' },
          stages: {
            type: 'array',
            description: 'Full breakdown, only when creating or restructuring',
            items: { type: 'object', required: ['name', 'steps'], properties: { name: { type: 'string' }, steps: { type: 'array', items: STEP_SCHEMA } } },
          },
          next: { type: 'boolean', description: 'Active step finished, start the next one' },
          done: { type: 'array', items: { type: 'string' }, description: 'Step titles now finished' },
          active: { type: 'string', description: 'Step title now in progress' },
          failed: { type: 'string', description: 'Step title that failed' },
          state: { enum: ['running', 'needs_input', 'error', 'done'] },
          note: { type: 'string', description: 'One line for needs_input or error' },
        },
      },
    })
    // one tick a second while anything moves: clocks, ETA, the terminal shimmer, strips folding
    $.clock.every(1000, async () => {
      const all = await read($, plans)
      const isMoving = all.some(p => p.state === 'running' || p.state === 'needs_input' || p.agents.some(a => a.endedAt === null))
      if (isMoving || agentHome.size > 0) await update($, tick, n => n + 1)
    })
    await $.command.register({ name: 'bars', description: 'Show or hide the progress bars' })
    await $.command.register({ name: 'bars-clear', description: 'Remove all progress bars' })
    await $.command.register({ name: 'bars-demo', description: 'Show a sample progress bar' })
    await syncStatus($)

    return next(e)
  })

  on('prompt.compose', async ($, e, next) => {
    const result = await next(e)
    return { sections: [...result.sections, { id: 'progress:rules', text: RULES, scope: 'session' as const }] }
  })

  on('turn.start', async ($, e, next) => {
    workCalls = 0
    sinceUpdate = 0
    isTouched = false
    isNudged = false
    return next(e)
  })

  // the person answering clears "needs input"; open bars ride along as one short context line
  on('prompt.submit', async ($, e, next) => {
    if (e.origin.kind !== 'composer') return next(e)
    const all = await read($, plans)
    if (all.some(p => p.state === 'needs_input')) {
      await update($, plans, xs => xs.map(p => (p.state === 'needs_input' ? { ...p, state: 'running' as const, note: null } : p)))
    }
    const open = all.filter(isOpenPlan)
    if (open.length === 0) return next(e)
    const line = `progress: open bars ${open.map(p => `${p.id} (${stageLabel(p)})`).join(', ')}`
    return next({ ...e, context: [...(e.context ?? []), line] })
  })

  // session name: the newest open bar's title, else a short Haiku name for the first prompt;
  // a name the person set themselves is never replaced
  on('classic.UserPromptSubmit', async ($, e, next) => {
    const result = await next(e)
    if (result.sessionTitle || (e.source !== undefined && e.source !== 'user')) return result
    const t = await read($, titleState)
    if (t.isUserOwned) return result
    const current = e.session_title?.trim()
    if (current && current !== t.last) {
      // someone else named it: the person (a rename) or a resumed session
      await update($, titleState, s => ({ ...s, isUserOwned: true }))
      return result
    }
    let title = (await read($, plans)).filter(isOpenPlan).at(-1)?.title ?? ''
    if (!title && t.last === null && e.prompt.trim().length > 0) {
      const named = await $.model.complete({ model: 'haiku', prompt: `${TITLE_PROMPT}${e.prompt.slice(0, 1500)}\n</request>`, maxTokens: 24, effort: 'low', timeoutMs: 4000 })
      if (named.isAnswered) title = str(named.text.replace(/["'`*#.]/g, ''), 60)
    }
    if (!title || title === t.last) return result
    await update($, titleState, s => ({ ...s, last: title }))
    return { ...result, sessionTitle: title }
  })

  on('tool.call', { tool: TOOL }, async ($, e) => {
    const raw = e as unknown as Raw
    const now = await $.clock.now()
    const id = slug(str(raw.id, 60) || str(raw.title, 60))
    const prev = (await read($, plans)).find(p => p.id === id) ?? null
    const next = normalize(raw, prev, now, id)
    if (next.stages.length === 0) return { deny: `track: no bar "${id}" yet; create it with title and stages.` }
    isTouched = true
    sinceUpdate = 0
    await putPlan($, next)
    const w = where(next)
    return { result: `${id}: ${w.finished}/${w.total}, ${next.state}${w.activeTitle && next.state !== 'done' ? `, active "${w.activeTitle}"` : ''}` }
  })

  on('tool.call', { tool: 'AskUserQuestion' }, async ($, e, next) => {
    const live = (await read($, plans)).filter(p => p.state === 'running' && p.id !== AGENTS).at(-1)
    const mark = (from: PlanState, to: PlanState) =>
      update($, plans, all => all.map(p => (p.id === live?.id && p.state === from ? { ...p, state: to } : p)))
    if (live) await mark('running', 'needs_input')
    const ran = await next(e)
    if (live) await mark('needs_input', 'running')
    return ran
  })

  // main loop: soft reminders only, never a refusal
  on('tool.call', async ($, e, next) => {
    if (e.agentId) {
      const agentId = e.agentId
      if (!agentHome.has(agentId)) return next(e)
      await editAgent($, agentId, a => ({ ...a, state: 'running', tool: String(e.tool).replace(/^mcp__[^_]+__/, '') }))
      if (e.tool_use_id) toolUses.set(e.tool_use_id, agentId)
      const ran = await next(e)
      if (e.tool_use_id) toolUses.delete(e.tool_use_id)
      await editAgent($, agentId, a => (a.state === 'waiting' ? { ...a, state: 'running' } : a))
      return ran
    }
    if (!WORK_TOOLS.has(String(e.tool))) return next(e)
    const ran = await next(e)
    if (ran.deny !== undefined || ran.isReadOnly) return ran
    workCalls += 1
    sinceUpdate += 1
    const hasLive = isTouched || (await read($, plans)).some(isOpenPlan)
    const note = (text: string) => ({ ...ran, context: [...(ran.context ?? []), text] })
    if (!hasLive && !isNudged && workCalls >= WORK_BEFORE_NUDGE) {
      isNudged = true
      return note(`progress: this task has several steps; create a bar with ${TOOL}.`)
    }
    if (hasLive && sinceUpdate >= CALLS_BEFORE_STALE) {
      sinceUpdate = 0
      return note('progress: the bar may be stale; send {id, next:true} if a step finished.')
    }
    return ran
  })

  on('agent.spawn', async ($, e, next) => {
    const started = await next(e)
    if (!('agentId' in started) || !started.agentId) return started
    const id = started.agentId
    const now = await $.clock.now()
    const parentHome = e.parentAgentId ? agentHome.get(e.parentAgentId) : undefined
    const home = parentHome ?? (await read($, plans)).filter(isOpenPlan).at(-1)?.id ?? AGENTS
    agentHome.set(id, home)
    const run: AgentRun = { id, title: (e.description || e.subagentType || 'Agent').slice(0, 60), state: 'running', tool: 'Starting', startedAt: now, endedAt: null }
    let isNew = false
    await update($, plans, all => {
      const host = all.find(p => p.id === home)
      if (host) {
        // a finished agents bar starts a fresh batch
        const agents = host.id === AGENTS && host.state !== 'running' ? [run] : [...host.agents, run]
        return all.map(p => (p.id === home ? { ...p, agents, ...(p.id === AGENTS ? { state: 'running' as const, doneAt: null } : {}) } : p))
      }
      isNew = true
      return placeBar(all, { id: AGENTS, title: 'Agents', stages: [], state: 'running', note: null, startedAt: now, doneAt: null, agents: [run] })
    })
    if (isNew) await update($, isOpen, () => true)
    return started
  })

  // a subagent held on a permission prompt turns amber until the call goes on
  on('tool.check', async ($, e, next) => {
    const verdict = await next(e)
    const useId = e.tool_use_id
    const agentId = useId ? toolUses.get(useId) : undefined
    if (agentId && useId && verdict.decision === 'ask') {
      // the mode often settles an ask in a blink; only a call still held after a moment waits on the person
      $.clock.after(600, async () => {
        if (toolUses.get(useId) === agentId) await editAgent($, agentId, a => ({ ...a, state: 'waiting', tool: 'Needs approval' }))
      })
    }
    return verdict
  })

  on('turn.complete', async ($, e, next) => {
    const agentId = e.agentId
    if (agentId && agentHome.has(agentId)) {
      const now = await $.clock.now()
      const isFailed = e.reason !== 'answer'
      const tool = e.reason === 'aborted' ? 'Stopped' : isFailed ? 'Failed' : 'Done'
      await editAgent($, agentId, a => ({ ...a, state: isFailed ? 'error' : 'done', tool, endedAt: now }))
      agentHome.delete(agentId)
    }
    if (!agentId) {
      // a plan whose steps are all finished closes itself
      for (const p of await read($, plans)) {
        const steps = p.stages.flatMap(s => s.steps)
        if (isOpenPlan(p) && steps.length > 0 && steps.every(s => isFinished(s.status))) {
          await putPlan($, { ...p, state: 'done', doneAt: await $.clock.now() })
        }
      }
    }
    return next(e)
  })

  on('command.run', { command: 'bars' }, async $ => {
    if ((await read($, plans)).length === 0) return { text: 'No bars yet. /bars-demo shows a sample.' }
    const open = await read($, isOpen)
    await update($, isOpen, () => !open)
    await syncStatus($)
    return { text: open ? 'Bars hidden; the status line shows the current step.' : 'Bars shown.' }
  })

  on('command.run', { command: 'bars-clear' }, async $ => {
    lastFill.clear()
    await update($, plans, () => [])
    await syncStatus($)
    return { text: 'Bars removed.' }
  })

  on('command.run', { command: 'bars-demo' }, async $ => {
    await putPlan($, DEMO(await $.clock.now()))
    await update($, isOpen, () => true)
    return { text: 'Sample bar shown above the prompt.' }
  })

  on('ui.render', { component: 'SessionMode' }, async ($, e, next) => {
    const count = (await read($, plans)).length
    const below = await next(e)
    if (count === 0) return below
    const open = await read($, isOpen)
    const { Box, Button } = $.ui.resolve(e)
    const press = async () => {
      await update($, isOpen, () => !open)
      await syncStatus($)
    }
    return (
      <Box flexDirection="row" alignItems="center" gap={1}>
        <Button key="bars-toggle" dimColor={!open} label={count > 1 ? `Bars ${count}` : 'Bars'} onPress={press} />
        {below}
      </Box>
    )
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const all = await read($, plans)
    if (all.length === 0 || e.props.hasSurvey || !(await read($, isOpen))) return next(e)
    const t = $.ui.resolve(e)
    const { Box, Button, Text } = t
    // the terminal's table answers Svg with an empty box, so its text drawing is chosen by surface
    const Svg = e.surface !== 'terminal' && 'Svg' in t ? t.Svg : null
    const n = await read($, tick)
    const now = await $.clock.now()
    const cols = Math.max(40, e.props.bodyColumns || 100)

    // shared column widths so every bar's track starts and ends at the same place
    const tracked = all.filter(p => p.state !== 'done' && p.id !== AGENTS)
    const titleCols = Math.min(Math.round(cols * 0.28), Math.max(8, ...all.map(p => p.title.length)))
    const metaCols = Math.max(0, ...tracked.map(p => stageLabel(p).length + 2 + timing(p, now).length))
    const trackCols = Math.max(10, cols - titleCols - metaCols - 14)

    const strips = (p: Plan) => {
      const v = visibleAgents(p, now)
      const rows = v.shown.map(a => {
        const c = AGENT_COLOR[a.state]
        const dot = a.state === 'running' ? (n % 2 === 0 ? '●' : '○') : a.state === 'done' ? '✓' : a.state === 'error' ? '✕' : '?'
        return (
          <Box key={`agent-${a.id}`} flexDirection="row" gap={1} paddingLeft={2}>
            <Text color={c}>{dot}</Text>
            <Text wrap="truncate">{a.title}</Text>
            <Text color={c}>{a.tool}</Text>
            <Box flexGrow={1} />
            <Text dimColor>{duration((a.endedAt ?? now) - a.startedAt)}</Text>
          </Box>
        )
      })
      if (v.hidden > 0) {
        rows.push(
          <Box key={`agents-more-${p.id}`} paddingLeft={2}>
            <Text dimColor>+{v.hidden} more</Text>
          </Box>,
        )
      }
      return rows
    }

    const bar = (p: Plan) => {
      const close = <Button key={`close-${p.id}`} plain dimColor label="✕" onPress={() => dropPlan($, p.id)} />
      if (p.state === 'done') {
        const steps = p.id === AGENTS ? p.agents.length : where(p).total
        const unit = p.id === AGENTS ? 'agent' : 'step'
        const label = `${p.title} · ${steps} ${unit}${steps === 1 ? '' : 's'} · ${duration((p.doneAt ?? now) - p.startedAt)}`
        const f = fadeOf(p, now)
        const W = (cols - 4) * PX_PER_COL
        return [
          <Box key={`bar-${p.id}`} flexDirection="row" gap={1}>
            {Svg ? (
              <Svg source={summarySvg(p, label, W, now)} alt={`✓ ${label}`} width={W} height={16} />
            ) : (
              <Text wrap="truncate">
                <Text color={STATE_COLOR.done} dimColor={f > 0.5}>
                  {dissolve('✓', f)}
                </Text>
                <Text dimColor>{` ${dissolve(label, f)}`}</Text>
              </Text>
            )}
            <Box flexGrow={1} />
            {f === 0 && close}
          </Box>,
        ]
      }
      if (p.id === AGENTS) {
        const ended = p.agents.filter(a => a.endedAt !== null).length
        return [
          <Box key={`bar-${p.id}`} flexDirection="row" gap={1}>
            <Text color={STATE_COLOR[p.state]}>{STATE_GLYPH[p.state]}</Text>
            <Text>Agents</Text>
            <Text dimColor>{`${ended}/${p.agents.length}`}</Text>
            <Box flexGrow={1} />
            {close}
          </Box>,
          ...strips(p),
        ]
      }
      const w = where(p)
      const pct = percent(p)
      const color = STATE_COLOR[p.state]
      const glyph = p.state === 'running' && n % 2 === 1 ? '○' : STATE_GLYPH[p.state]
      const alt = `${p.title}: ${stageLabel(p)}, ${pct}%${p.note ? ` — ${p.note}` : ''}`
      const track = Svg ? (
        <Svg source={trackSvg(p, trackCols * PX_PER_COL)} alt={alt} width={trackCols * PX_PER_COL} height={TRACK_H} />
      ) : (
        <Text>
          {trackText(p, trackCols, n).map(s => (
            <Text color={s.color} dimColor={s.dim}>
              {s.text}
            </Text>
          ))}
        </Text>
      )
      const rows = [
        <Box key={`bar-${p.id}`} flexDirection="row" alignItems="center" gap={1}>
          <Text color={color}>{glyph}</Text>
          <Box width={titleCols} flexShrink={0}>
            <Text wrap="truncate">{p.title}</Text>
          </Box>
          {track}
          <Box width={metaCols} flexShrink={0}>
            <Text color={p.state === 'running' ? stageColor(w.stage) : color} wrap="truncate">
              {stageLabel(p)}
            </Text>
            <Text dimColor wrap="truncate">{`  ${timing(p, now)}`}</Text>
          </Box>
          <Text dimColor>{`${String(pct).padStart(3, ' ')}%`}</Text>
          {close}
        </Box>,
      ]
      if (p.note && p.state !== 'running') {
        rows.push(
          <Box key={`note-${p.id}`} paddingLeft={2}>
            <Text color={color}>{`↳ ${p.note}`}</Text>
          </Box>,
        )
      }
      return [...rows, ...strips(p)]
    }

    return (
      <Box flexDirection="column">
        {all.flatMap(bar)}
      </Box>
    )
  })
}
