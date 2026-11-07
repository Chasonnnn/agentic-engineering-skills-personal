export const meta = {
  name: 'retro-week',
  description: 'Run the /retro skill over all Claude Code sessions from the past N days, grouped by repo',
  whenToUse: 'Weekly retrospective across sessions. args: {days: 7, today: "YYYY-MM-DD"}',
  phases: [
    { title: 'Inventory', detail: 'list recent sessions, group by repo' },
    { title: 'Retro', detail: 'one agent per repo group' },
    { title: 'Synthesize', detail: 'dedupe and rank across repos' },
    { title: 'Verify', detail: 'check each candidate against current repo state' },
  ],
}

const DAYS = (args && args.days) || 7
const TODAY = (args && args.today) || 'unknown'
const MAX_GROUPS = (args && args.maxGroups) || 6
const RETRO_SKILL = '/Users/chason/agentic-engineering-skills-personal/retro/SKILL.md'

const INVENTORY = {
  type: 'object',
  properties: {
    groups: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          repo: { type: 'string', description: 'absolute repo root path' },
          claudeSessions: { type: 'array', items: { type: 'string' }, description: 'absolute .jsonl paths' },
          codexSessionCount: { type: 'integer' },
          totalMB: { type: 'number' },
        },
        required: ['repo', 'claudeSessions', 'codexSessionCount', 'totalMB'],
      },
    },
  },
  required: ['groups'],
}

const CANDIDATES = {
  type: 'object',
  properties: {
    candidates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          category: { type: 'string', enum: ['navigation', 'automated-checks', 'coding-standards', 'global-agents-md', 'tool-economy', 'no-ops', 'information-access'] },
          title: { type: 'string' },
          repo: { type: 'string', description: 'repo root, or "global" for ~/.claude or ~/.agents scope' },
          evidence: { type: 'array', items: { type: 'string' }, description: 'session file + short quote or tool-call summary, one per item' },
          occurrences: { type: 'integer', description: 'how many sessions show this' },
          proposedChange: { type: 'string', description: 'concrete change: which file, which check, what text' },
          targetFile: { type: 'string' },
          mechanical: { type: 'boolean', description: 'true if a deterministic check can enforce it' },
          severity: { type: 'integer', minimum: 1, maximum: 5, description: '5 = large repeated cost or real errors shipped' },
        },
        required: ['category', 'title', 'repo', 'evidence', 'occurrences', 'proposedChange', 'targetFile', 'mechanical', 'severity'],
      },
    },
    sessionsRead: { type: 'integer' },
    sessionsSkipped: { type: 'array', items: { type: 'string' } },
  },
  required: ['candidates', 'sessionsRead', 'sessionsSkipped'],
}

const VERDICTS = {
  type: 'object',
  properties: {
    verdicts: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          status: { type: 'string', enum: ['confirmed', 'already-addressed', 'evidence-wrong', 'not-worth-it'] },
          reason: { type: 'string' },
          revisedChange: { type: 'string', description: 'corrected proposal if the original was imprecise; empty otherwise' },
        },
        required: ['title', 'status', 'reason', 'revisedChange'],
      },
    },
  },
  required: ['verdicts'],
}

const LOG_HINTS = `Session logs are JSONL and some are 50+ MB. Do NOT Read whole files. Use jq/grep/rg via Bash to extract signal, e.g.:
- user turns: jq -c 'select(.type=="user" and (.message.content|type)=="string") | .message.content[0:400]'
- tool calls by name: jq -r 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | .name' | sort | uniq -c
- tool errors: jq -c 'select(.type=="user") | .message.content[]? | select(.type=="tool_result" and .is_error==true) | .content' | cut -c1-300
- large tool results: measure length of tool_result content and list the biggest with their tool names
- repeated searches for the same file/symbol (Grep/Glob/find patterns) signal navigation gaps
- user corrections ("no", "wrong", "I said", "stop", interruptions) signal steering gaps
Codex sessions for the same repo live under ~/.codex/sessions (match the "cwd" field); sample a few only if they add evidence about delegated work.`

phase('Inventory')
const inv = await agent(
  `List Claude Code session logs modified in the past ${DAYS} days (today is ${TODAY}).
Files: ~/.claude/projects/*/*.jsonl (top level only, skip subagents/ dirs), size > 20 KB, mtime within ${DAYS} days.
Group them by repo root: merge worktree project dirs (e.g. "-Users-chason-X--claude-worktrees-foo", "-Users-chason--herdr-worktrees-X-...") into the repo they belong to (/Users/chason/X). Recover the real path from the "cwd" field inside the jsonl when the dir name is ambiguous (spaces become dashes).
Also count Codex sessions under ~/.codex/sessions with mtime within ${DAYS} days whose cwd is inside each repo.
Exclude current workflow/retro sessions and app-support scratch dirs (Library-Application-Support-*) unless they hold substantial work.
Return groups sorted by totalMB descending.`,
  { label: 'inventory', schema: INVENTORY, effort: 'low' }
)

let groups = (inv && inv.groups) || []
if (!groups.length) return { error: 'no sessions found' }
if (groups.length > MAX_GROUPS) {
  const keep = groups.slice(0, MAX_GROUPS - 1)
  const rest = groups.slice(MAX_GROUPS - 1)
  keep.push({
    repo: 'misc: ' + rest.map(g => g.repo).join(', '),
    claudeSessions: rest.flatMap(g => g.claudeSessions),
    codexSessionCount: rest.reduce((a, g) => a + g.codexSessionCount, 0),
    totalMB: rest.reduce((a, g) => a + g.totalMB, 0),
  })
  groups = keep
  log(`Merged ${rest.length} small repo groups into one misc group`)
}
log(`${groups.length} groups, ${groups.reduce((a, g) => a + g.claudeSessions.length, 0)} Claude sessions`)

phase('Retro')
const retros = await parallel(groups.map((g, i) => () =>
  agent(
    `Run a retrospective following ${RETRO_SKILL} (read it first) over these sessions from the past ${DAYS} days.
Repo: ${g.repo}
Claude sessions (${g.claudeSessions.length}, ${g.totalMB} MB):
${g.claudeSessions.join('\n')}
Codex sessions in this repo: ${g.codexSessionCount}

${LOG_HINTS}

Read the repo's CLAUDE.md/AGENTS.md, CODING_STANDARDS.md, package scripts, pre-commit config and CI workflows before proposing checks, so an existing-but-unwired check is the finding. Global steering lives in ~/.claude/CLAUDE.md and ~/.agents/skills; tag those candidates repo="global".
Prefer patterns that recur across sessions over one-offs. Every candidate needs concrete evidence (session file + quote/summary). Read-only: do not edit any file.
If you skip sessions for size or time, list them in sessionsSkipped.`,
    { label: `retro:${g.repo.split('/').pop().slice(0, 30)}`, phase: 'Retro', schema: CANDIDATES }
  )
))

const all = retros.filter(Boolean).flatMap(r => r.candidates)
const skipped = retros.filter(Boolean).flatMap(r => r.sessionsSkipped)
const failedGroups = groups.filter((g, i) => !retros[i]).map(g => g.repo)
if (failedGroups.length) log(`Retro failed for: ${failedGroups.join(', ')}`)
if (skipped.length) log(`${skipped.length} sessions skipped by retro agents`)
if (!all.length) return { groups, candidates: [], skipped, failedGroups }

phase('Synthesize')
const merged = await agent(
  `Merge these retrospective candidates from ${groups.length} repo groups into one list.
- Merge duplicates (same root cause across repos → one candidate, repo="global" if it is a global-config or shared-skill fix; sum occurrences, keep the best evidence).
- Keep repo-specific items separate.
- Re-score severity 1-5 on cost x frequency. Rank most severe first.
- Mechanical violations must propose a deterministic check, not a CLAUDE.md rule.
Candidates JSON:
${JSON.stringify(all)}`,
  { label: 'synthesize', phase: 'Synthesize', schema: CANDIDATES }
)
const ranked = ((merged && merged.candidates) || all).sort((a, b) => b.severity - a.severity)

phase('Verify')
const ver = await agent(
  `Adversarially verify each retrospective candidate against the CURRENT state of the files. Default to rejecting when evidence is weak.
For each: open the target file / repo config / CI workflow. Mark "already-addressed" if the fix already exists (e.g. landed after the session), "evidence-wrong" if the quoted evidence does not support the claim (spot-check one evidence item in the session log with grep), "not-worth-it" if the change costs more context or maintenance than it saves, else "confirmed". Fix imprecise proposals in revisedChange (exact file path, exact check command).
Read-only: do not edit any file.
Candidates JSON:
${JSON.stringify(ranked)}`,
  { label: 'verify', phase: 'Verify', schema: VERDICTS }
)

const byTitle = new Map(((ver && ver.verdicts) || []).map(v => [v.title, v]))
const results = ranked.map(c => ({ ...c, verdict: byTitle.get(c.title) || null }))
return {
  confirmed: results.filter(r => r.verdict && r.verdict.status === 'confirmed'),
  rejected: results.filter(r => r.verdict && r.verdict.status !== 'confirmed').map(r => ({ title: r.title, repo: r.repo, status: r.verdict.status, reason: r.verdict.reason })),
  unverified: results.filter(r => !r.verdict).map(r => r.title),
  coverage: { groups: groups.map(g => ({ repo: g.repo, sessions: g.claudeSessions.length, mb: g.totalMB })), skipped, failedGroups },
}
