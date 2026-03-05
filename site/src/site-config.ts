import type { SiteConfig } from '@mcptoolshop/site-theme';

export const config: SiteConfig = {
  title: 'XRPL Camp',
  description: 'Learn the XRP Ledger in one sitting — wallet, payment, verification, certificate in 10 minutes.',
  logoBadge: 'XC',
  brandName: 'XRPL Camp',
  repoUrl: 'https://github.com/mcp-tool-shop-org/xrpl-camp',
  pypiUrl: 'https://pypi.org/project/xrpl-camp/',
  footerText: 'MIT Licensed — built by <a href="https://mcp-tool-shop.github.io/" style="color:var(--color-muted);text-decoration:underline">MCP Tool Shop</a>',

  hero: {
    badge: 'Open source',
    headline: 'XRPL Camp',
    headlineAccent: 'learn the ledger in one sitting.',
    description: 'Walk through 6 lessons — from "what is a ledger?" to a funded wallet, a confirmed payment, and a portable certificate. No accounts. No real money. About 10 minutes.',
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
        { title: 'Wallet', desc: 'Generate a Testnet keypair, fund it from the faucet, and see your balance — all from the CLI.' },
        { title: 'Payment', desc: 'Send a self-payment with a custom memo. One drop, one transaction, permanently on the ledger.' },
        { title: 'Certificate', desc: 'Get a portable, verifiable certificate and a tamper-evident proof pack with SHA-256 integrity hash.' },
      ],
    },
    {
      kind: 'code-cards',
      id: 'usage',
      title: 'Usage',
      cards: [
        { title: 'Install', code: 'pipx install xrpl-camp\n# or: pip install xrpl-camp' },
        { title: 'Guided flow', code: 'xrpl-camp start\n\n# Walk through all 6 lessons:\n# 1. Mental Model\n# 2. Create Wallet\n# 3. Fund Wallet\n# 4. Send Payment\n# 5. Verify Transaction\n# 6. Certificate' },
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
        ['xrpl-camp wallet create', 'Create a Testnet wallet'],
        ['xrpl-camp fund', 'Fund via the Testnet faucet'],
        ['xrpl-camp send --memo "hello"', 'Self-payment with custom memo'],
        ['xrpl-camp verify --tx <hash>', 'Verify a transaction on-ledger'],
        ['xrpl-camp certificate', 'Generate certificate + proof pack'],
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
