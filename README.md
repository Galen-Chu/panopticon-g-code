# 👁️ Panopticon G-Code

> **"The observer and the observed are one."** · 「觀察者與被觀察者是一體的。」

---

## 🧭 Project Philosophy · 專案理念

Panopticon G-Code is a **dual-axis awareness system** rooted in the
philosophical concept of the Panopticon (Foucault) — reimagined not as a
prison of surveillance, but as a **mirror of self-observation**.

Panopticon G-Code 是一個**雙軸意識觀察系統**，根植於傅柯的「全景敞視監獄」哲學概念——重新詮釋為**自我觀察的鏡子**，而非監控的牢籠。

The G-Code ecosystem is itself a manifestation of personal consciousness
growth. Panopticon watches this ecosystem the way consciousness watches
itself: with curiosity, without judgment, and with the intent to grow.

G-Code 生態系統本身就是個人意識成長的具現。Panopticon 觀看這個生態，如同意識觀看自己：帶著好奇、不帶批判、以成長為意圖。

### Key Metaphors · 核心隱喻

| Metaphor | Meaning · 意義 |
|----------|---------------|
| The Watchtower · 瞭望塔 | Awareness that observes without being observed back |
| The Mirror · 鏡子 | Self-reflection that reveals patterns |
| The Feedback Loop · 回饋迴路 | Observation → Insight → Adjustment → New Observation |
| The Ecosystem Pulse · 生態脈搏 | Health of the G-Code family as a living system |

---

## 🏗️ Dual-Axis Architecture · 雙軸架構

```
         ┌─────────────────────────────────────┐
         │       PANOPTICON G-CODE             │
         │                                     │
         │   ┌─────────┐     ┌─────────┐      │
         │   │ INNER   │     │ OUTER   │      │
         │   │ AXIS    │◄───►│ AXIS    │      │
         │   │ (內觀)  │     │ (外監)  │      │
         │   └────┬────┘     └────┬────┘      │
         │        │               │            │
         │        ▼               ▼            │
         │  Self-Reflection  Ecosystem       │
         │  & Pattern        Monitoring      │
         │  Recognition      & Health        │
         │        │               │            │
         │        └───────┬───────┘            │
         │                │                    │
         │                ▼                    │
         │        Feedback Loop                │
         │        (回饋修正)                    │
         └─────────────────────────────────────┘
```

### Inner Axis (內觀) — Personal Consciousness Observation

- **Self-Reflection Journal**: Daily prompts for conscious awareness
- **Pattern Recognition**: Identify recurring thoughts, emotions, behaviors
- **Insight Generation**: Transform raw observations into actionable wisdom
- **CLI-First**: Headless, terminal-based, cron-compatible

### Outer Axis (外監) — G-Code Ecosystem Monitoring

- **Health Dashboard**: Real-time status of all G-Code repositories
- **CI/CD Monitoring**: Pipeline health across the ecosystem
- **Dependency Awareness**: Cross-repo impact analysis
- **Visual Observatory**: D3.js/Plotly interactive dashboard

### Feedback Loop (回饋修正)

Observations from both axes feed into each other:
- Personal insights → inform ecosystem priorities
- Ecosystem health → reveals personal patterns
- Continuous adjustment → growth in both dimensions

---

## 📦 Module Map · 模組地圖

| Module | Focus | Technology |
|--------|-------|-----------|
| `inner/journal` | Self-reflection prompts & entries | Python CLI |
| `inner/patterns` | Pattern detection in behavior | Python + ML |
| `inner/insights` | Insight generation from data | Gemini AI |
| `outer/monitor` | G-Code repo health checker | Python + GitHub API |
| `outer/dashboard` | Ecosystem visualization | D3.js / Plotly |
| `outer/alerts` | Anomaly detection & alerts | Python + Webhooks |
| `core/feedback` | Bidirectional feedback engine | Python |

---

## 🚀 Quick Start · 快速開始

### Prerequisites

- Python 3.11+
- GitHub CLI (`gh`) for ecosystem monitoring
- Google Gemini API key (optional, for AI insights)

### Installation

```bash
git clone https://github.com/Galen-Chu/panopticon-g-code.git
cd panopticon-g-code
python -m venv venv
source venv/bin/activate    # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### Inner Axis — Daily Self-Reflection

```bash
# Start today's reflection
python -m inner.journal --today

# Review patterns from the last 30 days
python -m inner.patterns --days 30

# Generate AI-powered insights
python -m inner.insights --gemma
```

### Outer Axis — Ecosystem Monitoring

```bash
# Check all G-Code repos' health
python -m outer.monitor --all

# Launch the visual dashboard
python -m outer.dashboard

# Set up automated alerts
python -m outer.alerts --configure
```

---

## 🔄 Related Projects · 關聯專案

Panopticon G-Code is a peer module in the G-Code ecosystem — it both
**monitors** the family and **receives feedback** from it:

| Repository | Relationship · 關係 |
|-----------|-------------------|
| [spec-g-code](https://github.com/Galen-Chu/spec-g-code) | Shared specifications |
| [skill-g-code](https://github.com/Galen-Chu/skill-g-code) | Routing via `[Panopticon]` prefix |
| [spiritual-g-code](https://github.com/Galen-Chu/spiritual-g-code) | Provides transit data for correlation |
| [sync-g-code](https://github.com/Galen-Chu/sync-g-code) | Shares daily automation patterns |
| [psychological-g-code](https://github.com/Galen-Chu/psychological-g-code) | Inner axis references chakra framework |
| [physiological-g-code](https://github.com/Galen-Chu/physiological-g-code) | Inner axis references hexagram patterns |
| [program-g-code](https://github.com/Galen-Chu/program-g-code) | Outer axis uses CI/CD toolkit |

---

## 🌐 Global Constraints

Inherited from the G-Code ecosystem:

- **Bilingual Imperative**: All output in English + Traditional Chinese (繁體中文)
- **CLI-First**: Prioritize headless, terminal-runnable tools
- **Rational Grounding**: Technical language, not mystical jargon
- **Feedback Required**: Every observation must have a pathway to action

---

## 🗺️ Development Plan

### Phase 1 — Foundation
- [x] Core directory structure & module stubs
- [x] Inner axis: journal CLI with daily prompts
- [x] Outer axis: GitHub API health checker
- [x] README + LICENSE

### Phase 2 — Inner Axis
- [x] Pattern recognition from journal entries
- [x] Gemini AI integration for insights
- [x] Reflection prompts library (bilingual)

### Phase 3 — Outer Axis
- [x] D3.js ecosystem dashboard
- [x] Automated CI/CD monitoring via GitHub Actions
- [x] Alert system (Slack/email/webhook)

### Phase 4 — Feedback Loop
- [x] Bidirectional data flow between axes
- [x] Correlation engine (inner patterns ↔ outer health)
- [x] Adaptive adjustment recommendations

---

## 📄 License

MIT — see [LICENSE](LICENSE).
