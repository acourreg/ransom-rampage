// 25 thematics × 25 domain traits × 25 contexts = 15 625 unique combinations

export const STARTUP_THEMATICS = [
  // original 20
  "neobank for freelancers who distrust banks (and accountants)",
  "crypto savings app for Gen Z with trust issues",
  "B2B expense management that your CFO hates",
  "micro-lending for SMBs rejected by actual banks",
  "insurtech for gig workers nobody else would cover",
  "fractional real estate for people priced out of real estate",
  "carbon credit marketplace where nobody checks the math",
  "payroll automation that still breaks on payday",
  "cross-border remittance at 'only' 2% fee",
  "BNPL for medical bills nobody can afford upfront",
  "robo-advisor that underperforms the S&P 500 confidently",
  "student loan refinancing platform run by ex-bankers",
  "digital wallet for the unbanked — backed by VCs in Monaco",
  "subscription revenue financing for SaaS companies burning cash",
  "embedded finance SDK shipped in a weekend hackathon",
  "commodity trading for retail investors who watched too much TV",
  "DeFi lending protocol with a 47-page whitepaper",
  "SME invoice factoring with a 'disrupting' pitch deck",
  "loyalty points monetization because your miles expire anyway",
  "open banking aggregator nobody asked for but here we are",
  // new 5
  "peer-to-peer FX for expats who never read the fine print",
  "on-demand salary advances for workers who spend it immediately",
  "ESG investment platform marketed to people who drive SUVs",
  "trade finance platform bridging emerging markets and PowerPoint decks",
  "digital mortgage broker whose AI rejected your last application",
]

export const DOMAIN_CHARACTERISTICS = [
  // original 20
  "targeting markets where regulators haven't caught up yet",
  "built on a blockchain nobody audited",
  "using AI risk scoring trained on vibes",
  "GDPR-compliant (mostly, allegedly)",
  "freshly Series B funded — runway unclear",
  "processing €10M/day on infra built in a sprint",
  "operating in 12 countries with 1 compliance officer",
  "riding a viral campaign their legal team didn't review",
  "still digesting a legacy bank acquisition from 2 years ago",
  "under regulatory investigation (proactive statement pending)",
  "pivoting from B2C to B2B mid-fiscal year",
  "in reputation recovery mode post-breach",
  "growing 300% YoY with a negative EBITDA they call 'investment'",
  "backed by a sovereign wealth fund with specific expectations",
  "IPO roadshow starting next quarter, God help them",
  "named defendant in a class action filed last Tuesday",
  "shipping a mobile app rated 2.1 stars",
  "operating without a permanent CTO since March",
  "running production on the IT budget of a medium dentist office",
  "freshly merged with their main competitor in a deal nobody approved",
  // new 5
  "onboarding 50k users per day with zero capacity planning",
  "ISO 27001 certified — the auditors didn't ask the right questions",
  "relying on a single third-party API that has 99.1% uptime (not enough)",
  "whose founding engineer left last month with full prod access",
  "under a 72-hour breach disclosure deadline they just missed",
]

export const OPERATIONAL_CONTEXTS = [
  "whose Slack is public and their staging env is on the same domain",
  "that outsourced their security to a contractor who ghosted them",
  "whose on-call rotation is one person, and they're on vacation",
  "that runs 14 microservices no one fully understands anymore",
  "with a board demanding a security audit they keep postponing",
  "that recently migrated to cloud and left the old servers running",
  "whose CI/CD pipeline has God-mode access to production",
  "where the CTO role is held by the co-founder's college roommate",
  "whose API keys are hardcoded in a public GitHub commit from 2021",
  "that stores customer PII in a spreadsheet on Google Drive",
  "whose prod database has no backups since the last restructure",
  "that just fired its DevSecOps team to cut burn rate",
  "where MFA is 'optional' because users complained it was annoying",
  "that sends plaintext passwords in welcome emails",
  "whose last pentest was conducted by an intern with Kali Linux",
  "that keeps its disaster recovery plan in a folder no one can find",
  "whose vendor contracts have zero security SLAs",
  "relying on a legacy VPN that hasn't been patched in 18 months",
  "that logs everything but monitors nothing",
  "where 'security review' means a Slack thumbs-up from the CTO",
  "whose customer support team has access to all accounts",
  "that uses the same password for all third-party integrations",
  "currently being migrated by two contractors with conflicting PRs open",
  "whose compliance dashboard is manually updated every quarter",
  "that just passed SOC 2 Type I and is ignoring Type II",
]

export const THREAT_AGENTS = [
  { id: 'script_kiddie',   name: 'Kevin from IT',          desc: "Thinks he's a hacker because he watched Mr. Robot twice" },
  { id: 'script_kiddie',   name: 'Hector the Intern',      desc: 'Armed with a YouTube tutorial and too much free time' },
  { id: 'script_kiddie',   name: 'DarkLord2009',           desc: "His mom doesn't know he's doing this on her laptop" },
  { id: 'opportunist',     name: 'Chad Hackerman',         desc: 'Found your IP on a forum. Has no idea what to do with it' },
  { id: 'opportunist',     name: 'Brenda from Accounting', desc: "Clicked a phishing link, now she's accidentally an insider threat" },
  { id: 'opportunist',     name: 'The Discount Hacker',    desc: 'Bought a €12 exploit kit on a Telegram group' },
  { id: 'organized_crime', name: 'Viktor & Associates',    desc: 'Professional. Patient. Definitely not in a hurry' },
  { id: 'organized_crime', name: 'The Syndicate',          desc: "They've done this 200 times. You are not special to them" },
  { id: 'organized_crime', name: 'Madame Zeroday',         desc: 'Runs a boutique ransomware operation. Surprisingly good reviews' },
  { id: 'nation_state',    name: 'Agent Romanov',          desc: 'Not confirmed. Officially denied. Definitely happening' },
  { id: 'nation_state',    name: 'The Alphabet Team',      desc: 'Three-letter agency. No, the other one' },
  { id: 'insider',         name: 'Disgruntled Dave',       desc: 'Still has his badge. HR is aware. IT is not' },
  { id: 'insider',         name: 'Ex-CTO Gary',            desc: "Left 6 months ago. Password policy said 'recommended' not 'required'" },
  { id: 'hacktivist',      name: 'Anonymous_404',          desc: 'Politically motivated. Technically mediocre. Very loud' },
  { id: 'hacktivist',      name: 'JusticeKeyboard',        desc: 'Believes your neobank is morally bankrupt. Has a point, actually' },
  { id: 'ransomware_gang', name: 'BitLocker Bob',          desc: 'Specializes in encrypting things people really need' },
  { id: 'ransomware_gang', name: 'The Encryptors LLC',     desc: "Registered in a jurisdiction you've never heard of" },
  { id: 'competitor',      name: 'Definitely Not FinCorp', desc: 'A competitor. Legally distinct. Morally ambiguous' },
  { id: 'ai_agent',        name: 'GPT-Malicious',          desc: 'An autonomous agent someone deployed and forgot to turn off' },
  { id: 'curious_dev',     name: 'Pradeep the Pentester',  desc: 'Self-appointed. Uninvited. Technically correct about everything' },
]

export function pickThreatAgent() {
  return THREAT_AGENTS[Math.floor(Math.random() * THREAT_AGENTS.length)]
}

export const GRAPH_SHAPES = [
  "star",
  "linear",
  "mesh",
  "siloed",
  "hub_and_spoke",
  "layered",
  "binary_tree",
]

export const NODE_COUNT_RANGE = { min: 4, max: 12 }

export function buildGenerationPrompt() {
  const thematic  = STARTUP_THEMATICS[Math.floor(Math.random() * STARTUP_THEMATICS.length)]
  const domain    = DOMAIN_CHARACTERISTICS[Math.floor(Math.random() * DOMAIN_CHARACTERISTICS.length)]
  const context   = OPERATIONAL_CONTEXTS[Math.floor(Math.random() * OPERATIONAL_CONTEXTS.length)]
  const shape     = GRAPH_SHAPES[Math.floor(Math.random() * GRAPH_SHAPES.length)]
  const nodeCount = Math.floor(Math.random() * (NODE_COUNT_RANGE.max - NODE_COUNT_RANGE.min + 1)) + NODE_COUNT_RANGE.min
  const threat    = pickThreatAgent()

  return {
    prompt:      `Generate a fintech startup: ${thematic}, ${domain}, ${context}`,
    shape,
    nodeCount,
    threatAgent: threat,
    meta: { thematic, domain, context, shape, nodeCount, threatName: threat.name, threatDesc: threat.desc },
  }
}
