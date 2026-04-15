import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'XRPL Camp',
  description: 'Learn the XRP Ledger in one sitting — real transactions, portable proof, 10 minutes.',
  logoBadge: 'XC',
  brandName: 'XRPL Camp',
  repoUrl: 'https://github.com/mcp-tool-shop-org/xrpl-camp',
  npmUrl: 'https://www.npmjs.com/package/@mcptoolshop/xrpl-camp',
  pypiUrl: 'https://pypi.org/project/xrpl-camp/',
  footerText: 'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>',

  hero: {
    badge: 'Open source',
    headline: 'XRPL Camp',
    headlineAccent: 'learn the ledger in one sitting.',
    description: 'Six lessons. Real transactions on a real ledger. A portable, tamper-evident certificate at the end. No accounts, no real money, about 10 minutes.',
    primaryCta: { href: '#usage', label: 'Get started' },
    secondaryCta: { href: 'handbook/', label: 'Read the Handbook' },
    previews: [
      { label: 'Install', code: 'pipx install xrpl-camp' },
      { label: 'Start', code: 'xrpl-camp start' },
      { label: 'Dry run', code: 'xrpl-camp start --dry-run' },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'features',
      title: 'Features',
      subtitle: 'Everything you need to understand the XRPL — nothing you don\'t.',
      features: [
        { title: 'Real transactions', desc: 'Create a wallet, fund it, write a permanent memo, and verify it on the ledger — not in a sandbox, on the actual Testnet.' },
        { title: 'Portable proof', desc: 'Certificate + proof pack with SHA-256 integrity hash. Anyone can verify completion without trusting screenshots.' },
        { title: 'Workshop-ready', desc: 'Guided flow with resume, dry-run preview, and facilitator triage view. Built for classrooms and self-study.' },
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Usage',
      cards: [
        { title: 'Install', code: 'npx @mcptoolshop/xrpl-camp start\n# or: pipx install xrpl-camp' },
        { title: 'Guided flow', code: 'xrpl-camp start\n\n# 1. Mental Model\n# 2. Create Wallet\n# 3. Fund Wallet\n# 4. Send Payment\n# 5. Verify Transaction\n# 6. Certificate' },
      ],
    },
    {
      kind: 'data-table',
      id: 'commands',
      title: 'Commands',
      subtitle: 'Every networked command supports --dry-run.',
      columns: ['Command', 'What it does'],
      rows: [
        ['xrpl-camp start', 'Guided flow through all 6 lessons'],
        ['xrpl-camp start --dry-run', 'Full flow without network calls'],
        ['xrpl-camp status', 'Visual progress checklist'],
        ['xrpl-camp status --detail', 'Facilitator triage view'],
        ['xrpl-camp wallet create', 'Create a Testnet wallet'],
        ['xrpl-camp fund', 'Fund via the Testnet faucet'],
        ['xrpl-camp send --memo "hello"', 'Self-payment with custom memo'],
        ['xrpl-camp verify --tx <hash>', 'Verify a transaction on-ledger'],
        ['xrpl-camp certificate', 'Generate certificate + proof pack'],
        ['xrpl-camp proof verify <file>', 'Verify proof pack integrity'],
        ['xrpl-camp reset', 'Wipe all state (typed confirmation)'],
      ],
    },
    {
      kind: 'features',
      id: 'safety',
      title: 'Safety',
      subtitle: 'Built for learning, not for losing.',
      features: [
        { title: 'Testnet only', desc: 'All transactions happen on the XRPL Testnet. Test XRP has no real value.' },
        { title: 'No seed leakage', desc: 'Your private key is stored locally and never included in certificates or proof packs.' },
        { title: 'No telemetry', desc: 'No analytics, no phone-home. The only network calls go to the XRPL Testnet.' },
      ],
    },
  ],
};
