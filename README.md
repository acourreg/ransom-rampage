#### RansomRampage 🛡️🤖
AI-Driven Cyber Crisis Simulation (PoC)

### 🎯 Concept
A strategic "serious game" where a CTO defends a FinTech infrastructure against AI-driven ransomware. Players must balance real-time security trade-offs (isolation, patching, scanning) against business constraints like revenue flow, GDPR compliance, and reputation.

### 🧠 AI Architecture
Multi-Agent (LangGraph): Orchestrates specialized CISO, SRE, and Hacker nodes to manage complex, cyclical reasoning.

Expert RAG (FAISS): Grounded in real-world knowledge—MITRE ATT&CK tactics, SRE patterns, and European regulatory frameworks.

Semantic Caching: Purifies game states into canonical forms to identify identical strategic situations, slashing inference costs.

Zero Hallucination: A deterministic engine using Pydantic for 1:1 UI mapping and structured data integrity.

### 🛠 Technical Stack
Language: Python

AI Frameworks: LangChain, LangGraph

Vector DB: FAISS

Models: OpenAI API, Pydantic (State Validation)

Visualization: Mermaid.js

### 📊 Current Status (PoC)
Deterministic Logic: Outcomes derive strictly from infrastructure traits and revenue flows—no random chance (RNG).

16 Specialized Actions: Fully implemented across security and audit roles.

Performance: Semantic cache achieves >0.99 similarity for strategic state purification.