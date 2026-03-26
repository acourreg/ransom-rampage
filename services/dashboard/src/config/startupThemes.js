export const STARTUP_THEMATICS = [
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
]

export const DOMAIN_CHARACTERISTICS = [
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
  const thematic   = STARTUP_THEMATICS[Math.floor(Math.random() * STARTUP_THEMATICS.length)]
  const domain     = DOMAIN_CHARACTERISTICS[Math.floor(Math.random() * DOMAIN_CHARACTERISTICS.length)]
  const shape      = GRAPH_SHAPES[Math.floor(Math.random() * GRAPH_SHAPES.length)]
  const nodeCount  = Math.floor(Math.random() * (NODE_COUNT_RANGE.max - NODE_COUNT_RANGE.min + 1)) + NODE_COUNT_RANGE.min
  const threat     = pickThreatAgent()

  return {
    prompt:      `Generate a fintech startup: ${thematic}, ${domain}`,
    shape,
    nodeCount,
    threatAgent: threat,
    meta: { thematic, domain, shape, nodeCount, threatName: threat.name, threatDesc: threat.desc },
  }
}
