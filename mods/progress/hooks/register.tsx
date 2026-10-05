import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { AgentRun, Plan, PlanStage, PlanState, StepStatus, TitleState } from '../types'

const TOOL = 'mcp__progress__track'
const plans = atom({ plugin: 'progress', key: 'plans' } as const, [])
const isOpen = atom({ plugin: 'progress', key: 'isOpen' } as const, true)
const tick = atom({ plugin: 'progress', key: 'tick' } as const, 0)
const titleState = atom({ plugin: 'progress', key: 'title' } as const, { last: null, isUserOwned: false, hasAsked: false } as TitleState)

const MAX_BARS = 3
const FADE_MS = 1500 // a finished bar fades out over this long once the next prompt is sent
const FADE_FRAMES = 10
const STRIP_LINGER_MS = 5000
const MAX_STRIPS = 4
const AGENTS = 'agents:auto' // slug() never yields ':', so no model id can take it
const PX_PER_COL = 8 // desktop reports about 8 CSS px per column

const ACCENT = '#7AA2F7'
const UNLIT = '#3A3936'
const DIM = '#8A8884'
const STATE_COLOR: Record<PlanState, string> = { running: ACCENT, needs_input: '#E0A33A', paused: DIM, error: '#E5484D', done: '#3FB68B' }
const STATE_GLYPH: Record<PlanState, string> = { running: '●', needs_input: '?', paused: '●', error: '!', done: '✓' }
const AGENT_COLOR: Record<AgentRun['state'], string> = { running: ACCENT, waiting: '#E0A33A', done: '#3FB68B', error: '#E5484D' }
const STATUSES: StepStatus[] = ['pending', 'active', 'done', 'error', 'skipped']

const RULES = `# Progress bars
Tasks needing more than ~3 edits or commands get a bar via ${TOOL}: create it once with a title and the full breakdown (2-7 stages with short steps, or one stage for a flat list; titles of at most 4 words, in the user's language), then update it with short calls only: {id, next:true} when the active step is finished, or {id, done:[...], active:"..."}, {id, failed:"...", note}. Send state "needs_input" with a note before asking the user to decide. When the work is finished, close the bar with {id, state:"done"} before the final reply. The bar title also becomes the session name, so make it describe the task. Never describe the bars to the user.`

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
  // any update ends a pause; the paused time stays out of the clock
  const pausedAt = prev?.state === 'paused' ? (prev.pausedAt ?? null) : null
  const pausedMs = (prev?.pausedMs ?? 0) + (pausedAt !== null && state !== 'paused' ? now - pausedAt : 0)

  return {
    id,
    title,
    stages,
    state,
    note: str(input.note, 160) || null,
    startedAt: prev?.startedAt ?? now,
    doneAt: state === 'done' ? (prev?.doneAt ?? now) : null,
    pausedAt: state === 'paused' ? (pausedAt ?? now) : null,
    pausedMs,
    fadeAt: null,
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

// lit share of the rule; a done bar is full even if the model closed it with steps open
const fraction = (p: Plan) => {
  const w = where(p)
  return p.state === 'done' ? 1 : w.finished / Math.max(1, w.total)
}

const percent = (p: Plan) => Math.round(fraction(p) * 100)

const duration = (ms: number) => {
  const sec = Math.max(0, Math.round(ms / 1000))
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m${String(sec % 60).padStart(2, '0')}s`
  return `${Math.floor(min / 60)}h${String(min % 60).padStart(2, '0')}m`
}

// 0 until the fade starts, 1 when the bar leaves
const fadeOf = (p: Plan, now: number) => (p.fadeAt ? Math.min(1, Math.max(0, (now - p.fadeAt) / FADE_MS)) : 0)

// terminal fade: characters drop out in a scattered order as f goes 0 -> 1
const scatter = (i: number) => {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453
  return x - Math.floor(x)
}
const dissolve = (text: string, f: number) => (f <= 0 ? text : [...text].map((c, i) => (scatter(i) < f ? ' ' : c)).join(''))

// the clock stops while a bar is paused or done
const elapsed = (p: Plan, now: number) => duration((p.doneAt ?? p.pausedAt ?? now) - p.startedAt - (p.pausedMs ?? 0))

const stageLabel = (p: Plan) => {
  const w = where(p)
  return `${p.stages[w.stage]?.name ?? ''} ${w.step}/${w.stageSize}`
}

// the words beside the title: where the work is, or what it waits on
function detail(p: Plan): string {
  const note = p.note ? ` · ${p.note}` : ''
  if (p.state === 'needs_input') return `Needs your input${note}`
  if (p.state === 'error') return `Failed${note}`
  if (p.state === 'done') {
    const total = where(p).total
    return `Completed · ${total} step${total === 1 ? '' : 's'}`
  }
  const active = where(p).activeTitle
  return `${p.state === 'paused' ? 'Paused · ' : ''}${stageLabel(p)}${active ? ` · ${active}` : ''}`
}

const isOpenPlan = (p: Plan) => p.id !== AGENTS && p.state !== 'done'

// ---------- drawing ----------

const LINE_H = 3
const NOTCH = 2

// where the lit part ended at the last draw, so a redraw glides from there; equal values keep the svg string stable
const lastFill = new Map<string, number>()

// desktop: one hairline, notched where stages meet; the lit part glides to its new edge and a shine runs over it;
// a fading bar animates its own opacity, and the string stays the same each frame so the animation runs once
function lineSvg(p: Plan, W: number, isFading: boolean): string {
  const w = where(p)
  const total = Math.max(1, w.total)
  const fx = fraction(p) * W
  const color = STATE_COLOR[p.state]
  const from = lastFill.get(p.id) ?? fx
  lastFill.set(p.id, fx)
  const glide =
    Math.abs(from - fx) > 0.5
      ? `<animate attributeName="width" from="${from.toFixed(1)}" to="${fx.toFixed(1)}" dur=".5s" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1" fill="freeze"/>`
      : ''
  let segs = ''
  let at = 0
  p.stages.forEach((s, i) => {
    const x0 = (at / total) * W + (i > 0 ? NOTCH / 2 : 0)
    at += s.steps.length
    const x1 = (at / total) * W - (i < p.stages.length - 1 ? NOTCH / 2 : 0)
    segs += `<rect x="${x0.toFixed(1)}" width="${Math.max(0, x1 - x0).toFixed(1)}" height="${LINE_H}" rx="1.5"/>`
  })
  const shine =
    p.state === 'running' && fx > 0
      ? `<rect width="${(W * 0.25).toFixed(1)}" height="${LINE_H}" fill="url(#shine)"><animate attributeName="x" from="${(-W * 0.25).toFixed(1)}" to="${W.toFixed(1)}" dur="2s" repeatCount="indefinite"/></rect>`
      : ''
  const fade = isFading
    ? `<animate attributeName="opacity" from="1" to="0" dur="${FADE_MS / 1000}s" calcMode="spline" keyTimes="0;1" keySplines=".4 0 .6 1" fill="freeze"/>`
    : ''
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${LINE_H}" viewBox="0 0 ${W} ${LINE_H}">
<defs><linearGradient id="shine"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<clipPath id="lit"><rect width="${fx.toFixed(1)}" height="${LINE_H}">${glide}</rect></clipPath></defs>
<g>${fade}<g fill="${UNLIT}">${segs}</g><g clip-path="url(#lit)"><g fill="${color}">${segs}</g>${shine}</g></g></svg>`
}

// terminal: a heavy rule, lit up to a half-cell head
function lineText(p: Plan, cols: number): { lit: string; rest: string } {
  const filled = Math.round(fraction(p) * cols)
  if (filled >= cols) return { lit: '━'.repeat(cols), rest: '' }
  if (filled === 0) return { lit: '', rest: '━'.repeat(cols) }
  return { lit: `${'━'.repeat(filled - 1)}╸`, rest: '━'.repeat(cols - filled) }
}

// strips that show: unfinished first, finished ones fold after a few seconds, failed ones stay
function visibleAgents(p: Plan, now: number): { shown: AgentRun[]; hidden: number } {
  const live = p.agents.filter(a => a.state !== 'done' || now - (a.endedAt ?? now) < STRIP_LINGER_MS)
  const ranked = [...live].sort((a, b) => Number(a.state === 'done') - Number(b.state === 'done'))
  return { shown: ranked.slice(0, MAX_STRIPS), hidden: Math.max(0, ranked.length - MAX_STRIPS) }
}

// ---------- engine glue ----------

// adds or replaces one bar by id; past MAX_BARS the oldest finished bars make room, open ones never do;
// computed inside update() from the latest list, so parallel writers do not drop each other
function placeBar(all: readonly Plan[], next: Plan): Plan[] {
  const rest = all.some(p => p.id === next.id) ? all.map(p => (p.id === next.id ? next : p)) : [...all, next]
  while (rest.length > MAX_BARS) {
    const doneAt = rest.findIndex(p => p.state === 'done' && p.id !== next.id)
    if (doneAt < 0) break
    rest.splice(doneAt, 1)
  }
  return rest
}

// drops what the module keeps per bar once the bar is gone
function forget(id: string) {
  lastFill.delete(id)
  for (const [agentId, home] of agentHome) if (home === id) agentHome.delete(agentId)
}

async function syncStatus($: EngineInterface) {
  const live = (await read($, plans)).filter(isOpenPlan).at(-1)
  if (!live || (await read($, isOpen))) return $.ui.status(undefined)
  const w = where(live)
  $.ui.status(`${live.title} · ${stageLabel(live)}${w.activeTitle ? ` · ${w.activeTitle}` : ''}`)
}

async function dropPlan($: EngineInterface, id: string) {
  forget(id)
  await update($, plans, all => all.filter(p => p.id !== id))
  await syncStatus($)
}

// a done bar holds until the next prompt; then every done bar fades out and leaves
async function fadeDoneBars($: EngineInterface) {
  const now = await $.clock.now()
  let fading: string[] = []
  await update($, plans, all => {
    fading = []
    return all.map(p => {
      if (p.state !== 'done' || p.fadeAt) return p
      fading.push(p.id)
      return { ...p, fadeAt: now }
    })
  })
  if (fading.length === 0) return
  // the terminal has no opacity: redraw a few frames while the fade runs
  for (let k = 1; k < FADE_FRAMES; k++) {
    $.clock.after((k * FADE_MS) / FADE_FRAMES, () => update($, tick, n => n + 1))
  }
  $.clock.after(FADE_MS, async () => {
    // a bar reopened during the fade has lost its fadeAt and stays
    const gone = (await read($, plans)).filter(p => fading.includes(p.id) && p.state === 'done' && p.fadeAt === now)
    for (const p of gone) forget(p.id)
    if (gone.length > 0) await update($, plans, all => all.filter(p => !gone.some(g => g.id === p.id)))
    await syncStatus($)
  })
}

async function putPlan($: EngineInterface, next: Plan) {
  let prev: Plan | undefined
  let evicted: string[] = []
  await update($, plans, all => {
    prev = all.find(p => p.id === next.id)
    const placed = placeBar(all, next)
    evicted = all.filter(p => !placed.some(x => x.id === p.id)).map(p => p.id)
    return placed
  })
  evicted.forEach(forget)
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
  const before = (await read($, plans)).find(p => p.id === home)?.agents.find(a => a.id === agentId)
  if (!before) return
  const after = change(before)
  if (after.state === before.state && after.tool === before.tool && after.endedAt === before.endedAt) return
  const now = await $.clock.now()
  await update($, plans, all =>
    all.map(p => {
      if (p.id !== home) return p
      const agents = p.agents.map(a => (a.id === agentId ? change(a) : a))
      if (p.id !== AGENTS) return { ...p, agents }
      // the mod's own bar is done once every agent on it has ended
      const isOver = agents.every(a => a.state === 'done' || a.state === 'error')
      return { ...p, agents, state: isOver ? (agents.some(a => a.state === 'error') ? 'error' : 'done') : 'running', doneAt: isOver ? now : null }
    }),
  )
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
    // one tick a second while anything moves: clocks, the pulsing glyph, strips folding
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
    const isPerson = e.source === undefined || e.source === 'user'
    // the person's next prompt fades the done bars
    if (isPerson) await fadeDoneBars($)
    const result = await next(e)
    if (result.sessionTitle || !isPerson) return result
    const t = await read($, titleState)
    if (t.isUserOwned) return result
    const current = e.session_title?.trim()
    if (current && current !== t.last) {
      // someone else named it: the person (a rename) or a resumed session
      await update($, titleState, s => ({ ...s, isUserOwned: true }))
      return result
    }
    let title = (await read($, plans)).filter(isOpenPlan).at(-1)?.title ?? ''
    if (!title && !t.hasAsked && t.last === null && e.prompt.trim().length > 0) {
      await update($, titleState, s => ({ ...s, hasAsked: true }))
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
    sinceUpdate = 0
    await putPlan($, next)
    const w = where(next)
    return { result: `${id}: ${w.finished}/${w.total}, ${next.state}${w.activeTitle && next.state !== 'done' ? `, active "${w.activeTitle}"` : ''}` }
  })

  on('tool.call', { tool: 'AskUserQuestion' }, async ($, e, next) => {
    const live = (await read($, plans)).filter(p => (p.state === 'running' || p.state === 'needs_input') && p.id !== AGENTS).at(-1)
    const mark = (from: PlanState, to: PlanState, note?: null) =>
      update($, plans, all => all.map(p => (p.id === live?.id && p.state === from ? { ...p, state: to, ...(note === null ? { note } : {}) } : p)))
    if (live?.state === 'running') await mark('running', 'needs_input')
    const ran = await next(e)
    // answered: back to work, the question's note goes with it
    if (live) await mark('needs_input', 'running', null)
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
    const hasLive = (await read($, plans)).some(isOpenPlan)
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
    const run: AgentRun = { id, title: (e.description || e.subagentType || 'Agent').slice(0, 60), state: 'running', tool: 'Starting', startedAt: now, endedAt: null }
    let home = AGENTS
    let isNew = false
    await update($, plans, all => {
      // the parent's bar, else the newest open bar, else the mod's own; a bar closed meanwhile is skipped
      const isLive = (h: string | undefined) => h !== undefined && h !== AGENTS && all.some(p => p.id === h && p.state !== 'done')
      home = [parentHome, all.filter(isOpenPlan).at(-1)?.id].find(isLive) ?? AGENTS
      isNew = false
      const host = all.find(p => p.id === home)
      if (host) {
        // a finished agents bar starts a fresh batch
        const agents = host.id === AGENTS && host.state !== 'running' ? [run] : [...host.agents, run]
        return all.map(p => (p.id === home ? { ...p, agents, ...(p.id === AGENTS ? { state: 'running' as const, doneAt: null } : {}) } : p))
      }
      isNew = true
      return placeBar(all, { id: AGENTS, title: 'Agents', stages: [], state: 'running', note: null, startedAt: now, doneAt: null, agents: [run] })
    })
    agentHome.set(id, home)
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
      // the main turn ended: a running plan whose steps are all finished closes itself, any other pauses
      const now = await $.clock.now()
      let isChanged = false
      await update($, plans, all => {
        isChanged = false
        return all.map(p => {
          const steps = p.stages.flatMap(s => s.steps)
          if (p.id === AGENTS || p.state !== 'running' || steps.length === 0) return p
          isChanged = true
          return steps.every(s => isFinished(s.status)) ? { ...p, state: 'done' as const, doneAt: now } : { ...p, state: 'paused' as const, pausedAt: now }
        })
      })
      if (isChanged) await syncStatus($)
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
    for (const p of await read($, plans)) forget(p.id)
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

    const isTerminal = Svg === null
    const dim = DIM

    // terminal rows share column widths, so every rule starts and ends at the same place
    const tracked = all.filter(p => p.id !== AGENTS)
    const titleCols = Math.min(Math.round(cols * 0.25), Math.max(8, ...tracked.map(p => p.title.length)))
    const detailCols = Math.min(Math.round(cols * 0.35), Math.max(8, ...tracked.map(p => detail(p).length)))
    const timeCols = Math.max(4, ...tracked.map(p => elapsed(p, now).length))
    const ruleCols = Math.max(8, cols - titleCols - detailCols - timeCols - 16)

    const strips = (p: Plan) => {
      const v = visibleAgents(p, now)
      const count = v.shown.length + (v.hidden > 0 ? 1 : 0)
      const branch = (i: number) => (isTerminal ? (i === count - 1 ? '└ ' : '├ ') : '')
      const rows = v.shown.map((a, i) => {
        const c = AGENT_COLOR[a.state]
        const dot = a.state === 'running' ? (n % 2 === 0 ? '●' : '○') : a.state === 'done' ? '✓' : a.state === 'error' ? '✕' : '?'
        const isEnded = a.state === 'done'
        return (
          <Box key={`agent-${a.id}`} flexDirection="row" gap={1} paddingLeft={2}>
            <Text dimColor>{branch(i)}</Text>
            <Text color={c}>{dot}</Text>
            <Text dimColor={isEnded} wrap="truncate">
              {a.title}
            </Text>
            <Text color={dim}>{isEnded ? 'done' : a.tool}</Text>
            <Box flexGrow={1} />
            <Text color={dim}>{duration((a.endedAt ?? now) - a.startedAt)}</Text>
          </Box>
        )
      })
      if (v.hidden > 0) {
        rows.push(
          <Box key={`agents-more-${p.id}`} flexDirection="row" gap={1} paddingLeft={2}>
            <Text dimColor>{branch(count - 1)}</Text>
            <Text color={dim}>{`+${v.hidden} more`}</Text>
          </Box>,
        )
      }
      return rows
    }

    const bar = (p: Plan) => {
      const f = fadeOf(p, now)
      const isFading = Boolean(p.fadeAt)
      const fade = (s: string) => dissolve(s, f)
      const close = !isFading ? <Button key={`close-${p.id}`} plain dimColor label="✕" onPress={() => dropPlan($, p.id)} /> : null
      if (p.id === AGENTS) {
        if (p.state === 'done') {
          const count = p.agents.length
          const label = `${p.title} · ${count} agent${count === 1 ? '' : 's'} · ${elapsed(p, now)}`
          return [
            <Box key={`bar-${p.id}`} flexDirection="row" gap={1}>
              <Text wrap="truncate">
                <Text color={STATE_COLOR.done}>{fade('✓')}</Text>
                <Text color={dim}>{` ${fade(label)}`}</Text>
              </Text>
              <Box flexGrow={1} />
              {close}
            </Box>,
          ]
        }
        const ended = p.agents.filter(a => a.endedAt !== null).length
        return [
          <Box key={`bar-${p.id}`} flexDirection="row" gap={1}>
            <Text color={STATE_COLOR[p.state]}>{STATE_GLYPH[p.state]}</Text>
            <Text bold>Agents</Text>
            <Text color={dim}>{`${ended}/${p.agents.length} done`}</Text>
            <Box flexGrow={1} />
            {close}
          </Box>,
          ...strips(p),
        ]
      }
      const pct = percent(p)
      const color = STATE_COLOR[p.state]
      // only a running bar blinks; paused, done and the rest hold still
      const glyph = p.state === 'running' && n % 2 === 1 ? '○' : STATE_GLYPH[p.state]
      const words = detail(p)
      const wordsColor = p.state === 'running' ? dim : color
      const pctText = `${String(pct).padStart(3, ' ')}%`
      const below = isFading ? [] : strips(p)

      if (isTerminal) {
        const rule = lineText(p, ruleCols)
        return [
          <Box key={`bar-${p.id}`} flexDirection="row" gap={1}>
            <Text color={color}>{fade(glyph)}</Text>
            <Box width={titleCols} flexShrink={0}>
              <Text bold wrap="truncate">
                {fade(p.title)}
              </Text>
            </Box>
            <Text>
              <Text color={color}>{fade(rule.lit)}</Text>
              <Text color={UNLIT}>{fade(rule.rest)}</Text>
            </Text>
            <Box width={detailCols} flexShrink={0}>
              <Text color={wordsColor} wrap="truncate">
                {fade(words)}
              </Text>
            </Box>
            <Box width={timeCols} flexShrink={0}>
              <Text color={dim}>{fade(elapsed(p, now))}</Text>
            </Box>
            <Text color={dim}>{fade(pctText)}</Text>
            {close}
          </Box>,
          ...below,
        ]
      }

      const W = (cols - 2) * PX_PER_COL
      const alt = `${p.title}: ${words}, ${pct}%`
      return [
        <Box key={`bar-${p.id}`} flexDirection="column" gap={1}>
          <Box flexDirection="row" alignItems="center" gap={1}>
            <Text color={color}>{fade(glyph)}</Text>
            <Text bold wrap="truncate">
              {fade(p.title)}
            </Text>
            <Text color={wordsColor} wrap="truncate">
              {fade(words)}
            </Text>
            <Box flexGrow={1} />
            <Text color={dim}>{fade(elapsed(p, now))}</Text>
            <Text>{fade(pctText)}</Text>
            {close}
          </Box>
          <Svg source={lineSvg(p, W, isFading)} alt={alt} width={W} height={LINE_H} isInteractive />
        </Box>,
        ...below,
      ]
    }

    return (
      <Box flexDirection="column" gap={1}>
        {all.flatMap(bar)}
      </Box>
    )
  })
}
