# AI Meeting Assistant

**Live Deployment:** [https://ai-meeting-assistant-hzp6gbfpbug6t6pxi2caep.streamlit.app/](https://ai-meeting-assistant-hzp6gbfpbug6t6pxi2caep.streamlit.app/)

An AI-powered meeting assistant that converts recorded meetings into accurate transcripts and structured meeting records using a coordinated multi-model pipeline.

---

## Overview

The **AI Meeting Assistant** simplifies meeting documentation by combining high-speed automated speech recognition with state-of-the-art large language models. From raw meeting audio recordings, it cleans up transcriptions, diarizes or attributes discussions, summarizes conversations into professional minutes of the meeting (MoM), and extracts actionable tasks and key decisions in both human-readable and machine-readable formats.

---

## Why This Pipeline?

| Problem in Existing Tools | Real-World Consequence | How Our Pipeline Solves It |
|---|---|---|
| **1. The "Hallucination & Phantom Deadline" Flaw** | In Otter/Zoom, if someone casually remarks "maybe we could look into Redis sometime", the LLM frequently invents: *"Action Item: Alex to migrate to Redis by EOD"*. | **Strict Grounding & Explicit Nulls:** In Stage 3, we force strict negative prompting and output constraints: missing owners/deadlines must be marked as `Unspecified` rather than guessed. Proposals are strictly isolated from consensus decisions. |
| **2. Technical Jargon Mangle (Compounding Errors)** | General STT models corrupt niche acronyms and tech terms (e.g., PostgreSQL → *"post gray sequel"*, gRPC → *"G RPC"*, Kubernetes → *"cooper netties"*). Standard tools feed this garbage directly into summarizers. | **Two-Stage Decoupled Pipeline:** We don't do single-shot summarization. Stage 1 (Deepgram Nova-2) handles acoustic diarization; Stage 2 (GPT OSS) specifically runs domain vocabulary refinement *before* any summaries are generated. |
| **3. The "Black Box" Auditability Problem** | Existing tools only show you the final summary or raw audio. When an action item looks wrong, you have no way to trace where the model got confused without re-listening to the entire hour. | **Dual-Transcript Lineage:** We persist and expose both the **Raw Acoustic Transcript** and the **Domain-Refined Transcript** side-by-side, so teams can audit every modification. |
| **4. Unstructured / Un-actionable Outputs** | Most tools dump walls of text with bold bullet points. You still have to manually copy-paste into Jira, Linear, or Notion. | **Dual-Format Parity (Human + Machine):** Simultaneously outputs formatted Markdown and strict JSON with identical schemas for direct webhook/API ingestion into ticketing systems. |

---

## Tech Stack

- **Speech-to-Text (STT):** [Deepgram Nova-2](https://deepgram.com/) — High-accuracy, low-latency automated speech transcription with smart formatting and speaker diarization.
- **LLM (Transcript Refinement):** [Groq](https://groq.com/) — GPT OSS for context-aware grammar correction, disfluency removal, speaker formatting, and terminology normalization.
- **LLM (Minutes & Insights Generation):** [Groq](https://groq.com/) — GPT OSS for high-level semantic analysis, executive summary generation, decision extraction, and action item tracking.
- **Frontend / UI:** [Streamlit](https://streamlit.io/) — Fast, responsive, and intuitive web application interface for uploading audio, configuring pipelines, inspecting intermediate outputs, and downloading records.

---

## Architecture

The system operates via a sequential multi-stage processing pipeline:

```text
┌─────────────────┐
│  Audio Upload   │ (MP3, WAV, M4A, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Deepgram STT   │ (Nova-2 Model)
└────────┬────────┘
         │ Raw Transcript
         ▼
┌───────────────────────────────┐
│   Groq LLM Stage 1            │ (GPT OSS)
│   (Transcript Refinement)     │
└────────┬──────────────────────┘
         │ Refined Transcript (Diarized & Polished)
         ▼
┌───────────────────────────────┐
│   Groq LLM Stage 2            │ (GPT OSS)
│   (Minutes / Decisions / Tasks│
└────────┬──────────────────────┘
         │ Structured Output (Markdown & JSON)
         ▼
┌─────────────────┐
│  Streamlit UI   │ (Interactive Display & Export)
└─────────────────┘
```

---

## Model Roles & Responsibilities

1. **Deepgram Nova-2 (Acoustic & Phonetic Layer)**
   - Transcribes raw audio into text with millisecond timestamps and word-level confidence scores.
   - Applies deep-learning-based speaker diarization to differentiate speakers.
   - Handles multi-accent speech, domain-specific vocabularies, and background noise filtering.

2. **Groq GPT OSS — Stage 1: Transcript Refinement**
   - Corrects acoustic misrecognitions using semantic context and meeting subject cues.
   - Cleans up speech disfluencies (fillers, false starts, stuttering) while preserving conversational meaning.
   - Formats conversation flow with clear speaker tags and cohesive paragraphs.

3. **Groq GPT OSS — Stage 2: Minutes, Decisions & Action Items**
   - Synthesizes meeting context into an executive summary and agenda breakdown.
   - Extracts consensus points, formal agreements, and architectural/business decisions.
   - Identifies concrete action items with assignees, deadlines, and dependencies.
   - Formats outputs strictly into human-readable Markdown and schema-validated JSON.

---

## Setup Instructions

### 1. Prerequisites
- Python 3.9 or higher installed on your system.
- Git (optional, for cloning).

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/ai-meeting-assistant.git
cd ai-meeting-assistant
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Obtain API Keys
- **Deepgram API Key:** Create a free account at [Deepgram Console](https://console.deepgram.com) and generate an API key.
- **Groq API Key:** Sign up at [Groq Console](https://console.groq.com) and create an API key.

### 5. Configure Environment Variables
Create or edit the `.env` file in the project root:
```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```
> *Alternatively, you can provide these API keys dynamically in the Streamlit application sidebar during runtime.*

### 6. Run the Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## Usage Workflow

1. **Input Audio:** Upload an audio file (MP3, WAV, M4A, OGG, or FLAC) via the Streamlit interface.
2. **Configure Settings:** (Optional) Select target language, toggle speaker diarization, or customize agenda prompts in the sidebar.
3. **Execute Pipeline:**
   - Click **Process Meeting**.
   - Monitor real-time status as the audio is transcribed by Deepgram, refined by Groq LLM Stage 1, and synthesized into meeting minutes by Groq LLM Stage 2.
4. **Review & Edit:**
   - Switch between **Raw Transcript**, **Refined Transcript**, and **Minutes of Meeting**.
   - Review key decisions and delegated action items.
5. **Export:** Download the generated minutes as a Markdown report (`.md`) or machine-parseable JSON (`.json`).

---

## Output Formats

### 1. Human-Readable Markdown (`.md`)
Includes:
- Meeting Metadata (Title, Date, Participants, Duration)
- Executive Summary
- Discussion Points & Topic Segments
- Key Decisions Made
- Action Items & Next Steps (Assignee, Task, Deadline)

### 2. Machine-Readable JSON (`.json`)
Structured schema suitable for CRM, Jira, Notion, or Slack webhooks:
```json
{
  "metadata": {
    "title": "Sprint Planning & Architecture Review",
    "date": "2026-10-05",
    "participants": ["Speaker 0", "Speaker 1"]
  },
  "summary": "High-level summary of the meeting topics and outcomes.",
  "decisions": [
    {
      "id": "DEC-001",
      "decision": "Adopt Deepgram Nova-2 for real-time transcription.",
      "context": "Benchmarked against alternatives for latency and word error rate."
    }
  ],
  "action_items": [
    {
      "id": "ACT-001",
      "task": "Benchmark end-to-end latency with GPT OSS.",
      "assignee": "Speaker 0",
      "due_date": "2026-10-10",
      "status": "Pending"
    }
  ]
}
```

---

## Error Handling & Resilience

- **Audio File Validation:** Verifies supported audio formats, file size limits, and basic audio integrity before sending to external APIs.
- **API Failure & Rate Limit Retries:** Implements structured exception handling with descriptive error messages in the UI for quota limits, network timeouts, or invalid keys.
- **Graceful Fallbacks:** If LLM Stage 1 refinement encounters an issue, Stage 2 can directly process the raw transcript to ensure meeting records are never lost.
- **Key Validation:** Immediate feedback in the sidebar if API keys are missing or malformed.

---

## Team & Contribution

- **Team Name:** Paradise
- **Contributors:** 
  - M Charan Sree Teja (`t.menni@iitg.ac.in`)
  - Adith Sreepuram (`r.sreepuram@iitg.ac.in`)
