import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const TOOL = 'mcp__progress__track'
const STAGES = [
  { name: 'Build', steps: [{ title: 'Scaffold', status: 'pending' }, { title: 'Bars', status: 'pending' }] },
  { name: 'Verify', steps: [{ title: 'Tests', status: 'pending' }] },
]
const PROPS = { hasSurvey: false, isWorking: true, maxRows: 20, bodyColumns: 120, scroll: undefined } as never

// the engine beneath: a clock, and a settings-hook chain with nothing configured
const world = (on: On) => {
  on('classic.UserPromptSubmit', async () => ({}))
  on('ui.status', async () => ({ value: undefined }) as never)
  // the engine's own band: one marker line
  on('ui.render', async ($, e) => {
    const { Text } = $.ui.resolve(e)
    return h(Text, {}, 'engine') as never
  })
  return mock.clock(on, { now: 1_000_000 })
}

test('a bar is created, advanced and closed by short updates', async ($, on) => {
  world(on)
  const made = await $.tool.call({ tool: TOOL, id: 'mod', title: 'Own progress mod', stages: STAGES } as never)
  expect(made.result).toBe('mod: 0/3, running, active "Scaffold"')
  const moved = await $.tool.call({ tool: TOOL, id: 'mod', next: true } as never)
  expect(moved.result).toBe('mod: 1/3, running, active "Bars"')
  const done = await $.tool.call({ tool: TOOL, id: 'mod', done: ['Bars', 'Tests'] } as never)
  expect(done.result).toBe('mod: 3/3, done')
})

test('an update to an unknown bar is refused', async ($, on) => {
  world(on)
  const ran = await $.tool.call({ tool: TOOL, id: 'nope', next: true } as never)
  expect(ran.deny).toContain('no bar "nope" yet')
})

test('bars draw on terminal and desktop', async ($, on) => {
  world(on)
  await $.tool.call({ tool: TOOL, id: 'mod', title: 'Own progress mod', stages: STAGES } as never)
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ plugin: 'progress', surface, component: 'AbovePrompt', props: PROPS })
    expect(await ui.find({ type: 'Text', text: /Own progress mod/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Build 1\/2/ })).toBeDefined()
    if (surface === 'terminal') expect(await ui.find({ type: 'Text', text: /━/ })).toBeDefined()
    else expect(((await ui.find({ type: 'Svg' })) as { props?: { isInteractive?: boolean } } | undefined)?.props?.isInteractive).toBe(true)
    expect(await ui.find({ type: 'Text', text: /left/ })).toBeUndefined()
    expect(await ui.find({ key: 'close-mod' })).toBeDefined()
    await ui.unmount()
  }
})

test('a finished bar shows a summary line, then leaves', async ($, on) => {
  const clock = world(on)
  await $.tool.call({ tool: TOOL, id: 'mod', title: 'Own progress mod', stages: STAGES } as never)
  await clock.advance(90_000)
  await $.tool.call({ tool: TOOL, id: 'mod', state: 'done' } as never)
  const ui = await $.ui.mount({ plugin: 'progress', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
  expect(await ui.find({ type: 'Text', text: /Own progress mod · 3 steps · 1m30s/ })).toBeDefined()
  await ui.unmount()
  await clock.advance(9_000)
  const after = await $.ui.mount({ plugin: 'progress', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
  expect(await after.find({ type: 'Text', text: /Own progress mod/ })).toBeUndefined()
  await after.unmount()
})

test('a finished bar fades: svg animation on desktop, dissolving text on the terminal', async ($, on) => {
  const clock = world(on)
  await $.tool.call({ tool: TOOL, id: 'mod', title: 'Own progress mod', stages: STAGES } as never)
  await $.tool.call({ tool: TOOL, id: 'mod', state: 'done' } as never)
  const desk = await $.ui.mount({ plugin: 'progress', surface: 'desktop', component: 'AbovePrompt', props: PROPS })
  const svg = (await desk.find({ type: 'Svg' })) as { props?: { source?: string } } | undefined
  expect(svg?.props?.source).toContain('attributeName="opacity" from="1" to="0" begin="6.5s"')
  await desk.unmount()
  await clock.advance(7_400)
  const term = await $.ui.mount({ plugin: 'progress', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
  expect(await term.find({ type: 'Text', text: /Own progress mod · 3 steps/ })).toBeUndefined()
  expect(await term.find({ type: 'Text', text: /\S/ })).toBeDefined()
  expect(await term.find({ key: 'close-mod' })).toBeUndefined()
  await term.unmount()
})

test('the session takes the open bar title', async ($, on) => {
  world(on)
  await $.tool.call({ tool: TOOL, id: 'mod', title: 'Own progress mod', stages: STAGES } as never)
  const first = await $.classic.UserPromptSubmit({ prompt: 'go on', source: 'user' })
  expect(first.sessionTitle).toBe('Own progress mod')
})

test('without a bar, Haiku names the session once', async ($, on) => {
  world(on)
  let calls = 0
  on('model.complete', async () => {
    calls += 1
    return { value: { isAnswered: true, text: 'Custom Progress Mod', usage: { input_tokens: 1, output_tokens: 1, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 } } } as never
  })
  const first = await $.classic.UserPromptSubmit({ prompt: 'build my own progress mod', source: 'user' })
  expect(first.sessionTitle).toBe('Custom Progress Mod')
  const second = await $.classic.UserPromptSubmit({ prompt: 'more', source: 'user', session_title: 'Custom Progress Mod' })
  expect(second.sessionTitle).toBeUndefined()
  expect(calls).toBe(1)
})

test('a name the person set is kept', async ($, on) => {
  world(on)
  await $.tool.call({ tool: TOOL, id: 'mod', title: 'Own progress mod', stages: STAGES } as never)
  const ran = await $.classic.UserPromptSubmit({ prompt: 'go on', source: 'user', session_title: 'My name' })
  expect(ran.sessionTitle).toBeUndefined()
})

test('a failed Haiku call is not repeated on later prompts', async ($, on) => {
  world(on)
  let calls = 0
  on('model.complete', async () => {
    calls += 1
    return { value: { isAnswered: false, reason: 'api-error', usage: { input_tokens: 0, output_tokens: 0, cache_creation_input_tokens: 0, cache_read_input_tokens: 0 } } } as never
  })
  await $.classic.UserPromptSubmit({ prompt: 'first', source: 'user' })
  await $.classic.UserPromptSubmit({ prompt: 'second', source: 'user' })
  expect(calls).toBe(1)
})

test('a bar the model marked needs_input runs again once the question is answered', async ($, on) => {
  world(on)
  on('tool.call', { tool: 'AskUserQuestion' }, async () => ({ result: 'answered' }) as never)
  await $.tool.call({ tool: TOOL, id: 'mod', title: 'Own progress mod', stages: STAGES } as never)
  await $.tool.call({ tool: TOOL, id: 'mod', state: 'needs_input', note: 'pick DB' } as never)
  await $.tool.call({ tool: 'AskUserQuestion', questions: [] } as never)
  const ui = await $.ui.mount({ plugin: 'progress', surface: 'terminal', component: 'AbovePrompt', props: PROPS })
  expect(await ui.find({ type: 'Text', text: /Needs your input/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /Build 1\/2 · Scaffold/ })).toBeDefined()
  await ui.unmount()
})
