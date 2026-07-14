/**
 * auto-course — the autonomous course-generation loop (Phase 4, Path B).
 *
 * Run with the Workflow tool, repo-agnostic via args:
 *   Workflow({ scriptPath: "<template>/generator/auto-course.workflow.js",
 *              args: { repoPath, systemName, srcHint, repoUrl } })
 * then assemble its JSON result:
 *   npm run assemble -- --in <result.json> --system <id> --repo <repoPath>
 * then PROVE it (the verification gate — faithful + true + effective):
 *   Workflow({ scriptPath: "<template>/generator/proof.workflow.js",
 *              args: { templateDir, system: <id>, bundlePath: "bundles/<id>/bundle.json", repoPath } })
 *
 * Pipeline: enumerate domains -> extract the data model (ER) -> (per domain) author a
 * module + VERIFY every snippet against real source, self-healing drift -> completeness
 * critic -> loop until comprehensive. Every agent is HARD-SCOPED to repoPath (the prompts
 * forbid touching the session cwd — the targeting fix after agents once anchored on the
 * wrong repo). Output is consumed by generator/assemble-bundle.ts.
 */
export const meta = {
  name: 'auto-course',
  description: 'Autonomously generate a grounded, comprehensive onboarding course from a cold repo (enumerate -> data model -> author+verify -> completeness loop)',
  phases: [
    { title: 'Enumerate', detail: 'scan the repo for all teachable domains' },
    { title: 'Data model', detail: 'extract the canonical entities + relationships (the ER backbone)' },
    { title: 'Author + verify', detail: 'author a module per domain; verify every snippet against real source, self-heal drift' },
    { title: 'Completeness', detail: 'critic re-scans for missing domains; loop until comprehensive' },
  ],
}

const { systemName, repoUrl, srcHint = 'src' } = args
// Target repo DEFAULTS to the current working directory (the repo you're in) — the natural
// `npx`-style behavior. Pass args.repoPath only to course a repo that ISN'T the cwd.
const repoPath = args.repoPath
const R = repoPath || '.'
// Audience knob (same contract as Path A): 'developer' (default, full rigor + code) or
// 'non-technical' (plain-English, analogy-first, NO code snippets — different prose, not hidden prose).
const audience = args.audience === 'non-technical' ? 'non-technical' : 'developer'
const SCOPE = repoPath
  ? `STRICT SCOPE: course ONLY the repository at ${repoPath}. Ignore the current working directory entirely — do NOT read, list, grep, or cite ANY file outside ${repoPath}. Start by listing ${repoPath} and ${repoPath}/${srcHint}. Cite every path repo-relative (no ${repoPath} prefix).`
  : `STRICT SCOPE: course the repository in your CURRENT WORKING DIRECTORY (the repo you are in). Start by listing the project root and ./${srcHint}. Stay inside this repo (its package.json / pyproject / .git root); do not wander elsewhere. Cite every path repo-relative.`

const DOMAIN = {
  type: 'object', additionalProperties: false,
  required: ['id', 'title', 'files', 'covers'],
  properties: {
    id: { type: 'string', description: 'kebab-case id' },
    title: { type: 'string' },
    files: { type: 'array', items: { type: 'string' }, description: 'repo-relative paths implementing this domain' },
    covers: { type: 'string' },
  },
}
const PLAN_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['systemName', 'oneLiner', 'elevatorPitch', 'domains'],
  properties: {
    systemName: { type: 'string' }, oneLiner: { type: 'string' }, elevatorPitch: { type: 'string' },
    outOfScope: { type: 'array', items: { type: 'string' } },
    domains: { type: 'array', items: DOMAIN },
  },
}
const REL = { type: 'object', additionalProperties: false, required: ['to', 'cardinality'], properties: { to: { type: 'string', description: 'another entity id' }, cardinality: { type: 'string', enum: ['one-to-one', 'one-to-many', 'many-to-one', 'many-to-many'] }, label: { type: 'string' } } }
const DM_ENTITY = { type: 'object', additionalProperties: false, required: ['id', 'name', 'definition'], properties: { id: { type: 'string' }, name: { type: 'string' }, definition: { type: 'string' }, relationships: { type: 'array', items: REL } } }
const DATAMODEL_SCHEMA = { type: 'object', additionalProperties: false, required: ['entities'], properties: { entities: { type: 'array', items: DM_ENTITY } } }

const CONCEPT = { type: 'object', additionalProperties: false, required: ['id', 'name', 'definition'], properties: { id: { type: 'string' }, name: { type: 'string' }, definition: { type: 'string' } } }
const CODE = { type: 'object', additionalProperties: false, required: ['sourcePath', 'language', 'snippet'], properties: { caption: { type: 'string' }, language: { type: 'string' }, sourcePath: { type: 'string' }, snippet: { type: 'string', description: 'VERBATIM from the file' } } }
const CALLOUT = { type: 'object', additionalProperties: false, required: ['variant', 'md'], properties: { variant: { type: 'string', enum: ['gotcha', 'note', 'warning', 'tip'] }, md: { type: 'string' } } }
const LESSON = { type: 'object', additionalProperties: false, required: ['title', 'prose'], properties: { title: { type: 'string' }, prose: { type: 'string' }, code: { type: 'array', items: CODE }, callout: CALLOUT } }
const OPTION = { type: 'object', additionalProperties: false, required: ['text', 'correct'], properties: { text: { type: 'string' }, correct: { type: 'boolean' }, ifChosen: { type: 'string' } } }
const MISC = { type: 'object', additionalProperties: false, required: ['trap', 'correction'], properties: { trap: { type: 'string' }, correction: { type: 'string' } } }
const QUIZ = { type: 'object', additionalProperties: false, required: ['prompt', 'options', 'explanation'], properties: { prompt: { type: 'string' }, options: { type: 'array', items: OPTION }, explanation: { type: 'string' }, misconception: MISC } }
const MODULE_SCHEMA = {
  type: 'object', additionalProperties: false,
  required: ['id', 'title', 'objective', 'concepts', 'lessons', 'quiz'],
  properties: {
    id: { type: 'string' }, title: { type: 'string' }, objective: { type: 'string' }, oneJob: { type: 'string' },
    concepts: { type: 'array', items: CONCEPT }, lessons: { type: 'array', items: LESSON }, quiz: { type: 'array', items: QUIZ },
  },
}
const VERIFY_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['allVerified', 'blocks'],
  properties: { allVerified: { type: 'boolean' }, blocks: { type: 'array', items: { type: 'object', additionalProperties: false, required: ['index', 'status'], properties: { index: { type: 'integer' }, sourcePath: { type: 'string' }, status: { type: 'string', enum: ['verified', 'drifted', 'missing-file'] }, correctedSnippet: { type: 'string' } } } } },
}
const CRITIC_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['complete', 'missingDomains'],
  properties: { complete: { type: 'boolean' }, rationale: { type: 'string' }, missingDomains: { type: 'array', items: DOMAIN } },
}

function applyVerification(m, v) {
  if (!v || !Array.isArray(v.blocks)) return m
  let i = 0, verified = 0
  ;(m.lessons || []).forEach((l) => {
    if (!Array.isArray(l.code)) return
    l.code.forEach((c) => {
      const verdict = v.blocks.find((b) => b.index === i)
      if (verdict) {
        if (verdict.status === 'verified') verified++
        else if (verdict.status === 'drifted' && verdict.correctedSnippet) { c.snippet = verdict.correctedSnippet; verified++ }
        else if (verdict.status === 'missing-file') c._drop = true
      }
      i++
    })
  })
  ;(m.lessons || []).forEach((l) => { if (Array.isArray(l.code)) l.code = l.code.filter((c) => !c._drop) })
  m._verified = verified
  m._total = i
  return m
}

phase('Enumerate')
const plan = await agent(
  `${SCOPE}\n\nScope a COMPREHENSIVE developer onboarding course for "${systemName}". Read the README, ${srcHint}/__init__.py (or index/entrypoint), and each module file under ${srcHint}/.\n\nReturn: a precise one-liner (what it does in real terms), an elevator pitch (2-4 sentences on the core model + the non-obvious parts a newcomer trips on), what is explicitly out of scope, and the COMPLETE set of teachable domains — one per major subsystem/feature. For each domain: a kebab id, a title, the real repo-relative files that implement it, and what it covers. Be exhaustive: a new contributor should understand the WHOLE system (typically 8-12 domains). Do NOT under-scope.`,
  { schema: PLAN_SCHEMA, label: 'enumerate' },
)

phase('Data model')
const dataModel = await agent(
  `${SCOPE}\n\nExtract the CANONICAL DATA MODEL of "${systemName}" — the core persistent / state entities a newcomer must hold in their head, NOT every concept. Read the model / schema / state-machine / type files under ${R}/${srcHint} (e.g. models, *-status, types, lib). Return entities: each {id (kebab), name, one-sentence definition} plus relationships [{to (another entity id you also list), cardinality, label}]. Aim for ~8-20 entities with real relationships — this is the ER backbone. Only include edges between entities you list.`,
  { schema: DATAMODEL_SCHEMA, label: 'data-model' },
)

const modules = []
const seen = new Set()
let toAuthor = plan.domains || []
for (let round = 0; round < 3; round++) {
  const batch = toAuthor.filter((d) => d && d.id && !seen.has(d.id))
  if (!batch.length) break
  batch.forEach((d) => seen.add(d.id))
  log(`Round ${round + 1}: authoring ${batch.length} domain(s): ${batch.map((d) => d.id).join(', ')}`)

  const authored = await pipeline(
    batch,
    (d) => agent(
      audience === 'non-technical'
        ? `${SCOPE}\n\nAuthor ONE module of a NON-TECHNICAL onboarding course for "${systemName}" (${plan.oneLiner}) — for PMs, designers, and stakeholders, NOT engineers.\n\nDOMAIN: ${d.title}\nCOVERS: ${d.covers}\nFILES (your ground truth to READ, never to quote): ${(d.files || []).join(', ')}\n\nREAD those files first so every claim is true, then produce a DraftModule in PLAIN ENGLISH:\n- concept-first lessons: short analogy-first prose (markdown) explaining what happens and why it matters in business terms — NO code snippets at all (leave lessons' code arrays empty), no jargon without a plain gloss; optionally a gotcha/note callout for a real trap phrased plainly.\n- the real concepts of this domain (id kebab, name, plain one-sentence definition a non-engineer understands).\n- 2-4 misconception quizzes in plain language: actual traps, each an MCQ with exactly one correct option + 1-2 distractors (each distractor an ifChosen correction), an explanation, and a {trap, correction}.\nEvery factual claim must still come from the real files you read. Be clear, honest, and concrete.`
        : `${SCOPE}\n\nAuthor ONE deep module of a developer onboarding course for "${systemName}" (${plan.oneLiner}).\n\nDOMAIN: ${d.title}\nCOVERS: ${d.covers}\nFILES: ${(d.files || []).join(', ')}\n\nREAD those files first. Then produce a DraftModule:\n- concept-first lessons: each a short prose explanation (markdown), then 1-3 REAL code snippets copied VERBATIM from the files (8-20 lines each, with the exact repo-relative sourcePath), and optionally a gotcha/note callout for a real trap.\n- the real concepts of this domain (id kebab, name, plain one-sentence definition).\n- 2-4 misconception quizzes: actual traps a newcomer hits, each an MCQ with exactly one correct option + 1-2 distractors (each distractor an ifChosen correction), an explanation, and a {trap, correction}.\nSnippets MUST be copied verbatim from the files (they are verified against source, including a line-exact check). Be deep, precise, and honest.`,
      { schema: MODULE_SCHEMA, label: `author:${d.id}`, phase: 'Author + verify' },
    ),
    (m) => {
      if (!m) return null
      const blocks = []
      ;(m.lessons || []).forEach((l) => (l.code || []).forEach((c) => blocks.push({ index: blocks.length, sourcePath: c.sourcePath, snippet: c.snippet })))
      if (!blocks.length) { m._verified = 0; m._total = 0; return m }
      const listing = blocks.map((b) => `--- block #${b.index} (sourcePath: ${b.sourcePath}) ---\n${b.snippet}`).join('\n\n')
      return agent(
        `${SCOPE}\n\nVerify the code snippets in a drafted course module against the REAL source. For EACH block below, read ${R}/<sourcePath> and decide:\n- 'verified' if the snippet faithfully appears (trivial whitespace / teaching-elision is fine),\n- 'drifted' if it does NOT — then provide a correctedSnippet copied VERBATIM from the real file (8-20 lines) that best teaches the same point,\n- 'missing-file' if the file does not exist.\nPrefer making each snippet an EXACT contiguous copy of source where possible (it earns a stronger grounding mark). Return one entry per block (by index) plus allVerified.\n\n${listing}`,
        { schema: VERIFY_SCHEMA, label: `verify:${m.id}`, phase: 'Author + verify' },
      ).then((v) => applyVerification(m, v))
    },
  )
  modules.push(...authored.filter(Boolean))

  phase('Completeness')
  const covered = modules.map((m) => `- ${m.id}: ${m.title}`).join('\n')
  const crit = await agent(
    `${SCOPE}\n\nA developer onboarding course for "${systemName}" currently has these modules:\n${covered}\n\nScan the repo (especially ${srcHint}/) and judge whether the course COMPREHENSIVELY covers the system for a new contributor. If a substantial subsystem/feature is NOT yet covered, return it in missingDomains (id, title, real files, what it covers). If coverage is genuinely complete, complete=true and missingDomains=[]. Be rigorous about real gaps; do not invent trivial ones.`,
    { schema: CRITIC_SCHEMA, label: `completeness:r${round + 1}` },
  )
  log(`Round ${round + 1}: ${modules.length} modules; complete=${crit.complete}; gaps=${(crit.missingDomains || []).length}`)
  if (crit.complete || !(crit.missingDomains || []).length) break
  toAuthor = crit.missingDomains
}

const totals = modules.reduce((a, m) => ({ verified: a.verified + (m._verified || 0), total: a.total + (m._total || 0) }), { verified: 0, total: 0 })
log(`DONE: ${modules.length} modules, ${(dataModel.entities || []).length} data-model entities, grounding ${totals.verified}/${totals.total} (in-loop)`)
return {
  system: { id: systemName, name: plan.systemName || systemName, oneLiner: plan.oneLiner, elevatorPitch: plan.elevatorPitch, outOfScope: plan.outOfScope || [], repoUrl, depth: audience === 'non-technical' ? 'L2' : 'L3', audience },
  dataModel,
  moduleCount: modules.length,
  verifiedTotals: totals,
  modules,
}
