import streamlit as st
import os
import json
import time
from typing import Optional, Dict, Any, Tuple
from deepgram import DeepgramClient
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up the page config
st.set_page_config(
    page_title="AI Meeting Assistant",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- Helper Functions -----------------

def get_audio_mime_type(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    mime_types = {
        ".mp3": "audio/mp3",
        ".wav": "audio/wav",
        ".m4a": "audio/m4a",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
        ".mp4": "video/mp4"
    }
    return mime_types.get(ext, "audio/wav")

def process_stage_1_deepgram(audio_bytes: bytes, mime_type: str, api_key: str) -> str:
    """Stage 1: Transcribe audio using Deepgram Nova-2 (SDK v7)."""
    try:
        client = DeepgramClient(api_key)
        
        # Use v7 SDK API: pass audio bytes and options as keyword arguments
        response = client.listen.v1.media.transcribe_file(
            request=audio_bytes,
            model="nova-2",
            smart_format=True,
            language="en",
            punctuate=True,
            diarize=True,
            paragraphs=True,
            utterances=True
        )
        
        # Try to extract utterances for speaker-labeled output
        if hasattr(response.results, 'utterances') and response.results.utterances:
            utterances = response.results.utterances
            raw_transcript = "\n".join([f"Speaker {u.speaker}: {u.transcript}" for u in utterances])
            return raw_transcript
            
        # Fall back to paragraphs transcript
        if response.results.channels and response.results.channels[0].alternatives:
            alt = response.results.channels[0].alternatives[0]
            if hasattr(alt, 'paragraphs') and alt.paragraphs and hasattr(alt.paragraphs, 'transcript'):
                return alt.paragraphs.transcript
            return alt.transcript
            
        return ""
    except Exception as e:
        raise Exception(f"Deepgram API Error: {str(e)}")

def process_stage_2_refine_transcript(raw_transcript: str, api_key: str) -> str:
    """Stage 2: Refine transcript using Groq."""
    try:
        client = Groq(api_key=api_key)
        
        system_prompt = (
            "You are a transcript refinement specialist. Your task is to correct recognition errors "
            "in domain-specific terms, acronyms, technical jargon, and proper nouns in the transcript below. "
            "Preserve the speaker's intended meaning, including names, numbers, negation, and commitments. "
            "Do NOT summarize or restructure. Do NOT change the speaker labels. Output only the corrected transcript."
        )
        
        completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_transcript}
            ],
            temperature=0.3,
            max_tokens=4096
        )
        return completion.choices[0].message.content or ""
    except Exception as e:
        raise Exception(f"Groq API Error (Stage 2): {str(e)}")

def process_stage_3_meeting_minutes(refined_transcript: str, api_key: str) -> Tuple[str, str]:
    """Stage 3: Generate meeting minutes in Markdown and JSON using Groq."""
    try:
        client = Groq(api_key=api_key)
        
        # Markdown prompt
        md_system_prompt = (
            "You are a meeting documentation specialist. From the provided meeting transcript, "
            "generate a structured meeting record. You MUST follow these rules strictly:\n"
            "1. Only include information explicitly stated in the transcript\n"
            "2. Do NOT invent or guess owners, deadlines, or assignments not mentioned\n"
            "3. Do NOT present proposals as agreed decisions\n"
            "4. If an owner or deadline was not stated, mark it as 'Unspecified'\n\n"
            "Output the following sections in clean markdown:\n"
            "## Meeting Summary\n"
            "A concise 2-4 sentence overview.\n\n"
            "## Meeting Minutes\n"
            "Organized chronological notes of what was discussed.\n\n"
            "## Key Decisions\n"
            "Bulleted list of decisions that were explicitly agreed upon.\n\n"
            "## Action Items\n"
            "A table with columns: | Task | Owner | Deadline | Status |\n"
            "Mark Owner and Deadline as 'Unspecified' if not explicitly mentioned."
        )
        
        md_completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": md_system_prompt},
                {"role": "user", "content": refined_transcript}
            ],
            temperature=0.2,
            max_tokens=4096
        )
        markdown_minutes = md_completion.choices[0].message.content or ""
        
        # JSON prompt
        json_system_prompt = (
            "You are a meeting documentation specialist. From the provided meeting transcript, "
            "generate a structured JSON object with exactly these keys: "
            '{"meeting_summary": "...", "minutes": ["..."], "key_decisions": ["..."], "action_items": [{"task": "...", "owner": "Unspecified", "deadline": "Unspecified", "status": "Pending"}]}. '
            "Only include information explicitly stated. Mark missing owners/deadlines as 'Unspecified'. "
            "Output ONLY valid JSON, no markdown fences."
        )
        
        json_completion = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=[
                {"role": "system", "content": json_system_prompt},
                {"role": "user", "content": refined_transcript}
            ],
            temperature=0.1,
            max_tokens=4096
        )
        
        json_content = json_completion.choices[0].message.content or "{}"
        if json_content.startswith("```json"):
            json_content = json_content[7:]
        if json_content.startswith("```"):
            json_content = json_content[3:]
        if json_content.endswith("```"):
            json_content = json_content[:-3]
            
        json_minutes = json_content.strip()
        
        return markdown_minutes, json_minutes
    except Exception as e:
        raise Exception(f"Groq API Error (Stage 3): {str(e)}")

# ----------------- UI Layout -----------------

def main():
    # Sidebar
    with st.sidebar:
        st.title("AI Meeting Assistant")
        st.write("An AI-powered Meeting Assistant for the Inter-IIT ML Bootcamp.")
        
        deepgram_key = st.text_input(
            "Deepgram API Key", 
            value=os.environ.get("DEEPGRAM_API_KEY", ""), 
            type="password"
        )
        
        groq_key = st.text_input(
            "Groq API Key", 
            value=os.environ.get("GROQ_API_KEY", ""), 
            type="password"
        )
        
        st.divider()
        st.write("### Tech Stack")
        st.write("- **Speech-to-Text**: Deepgram Nova-2")
        st.write("- **LLM**: Groq (Llama-3.1-70b-versatile)")
        st.write("- **UI**: Streamlit")

    # Main Area
    st.header("AI Meeting Assistant")
    
    uploaded_file = st.file_uploader(
        "Upload a meeting recording", 
        type=["mp3", "wav", "m4a", "ogg", "flac", "webm", "mp4"]
    )

    if uploaded_file is not None:
        file_size = uploaded_file.size
        if file_size == 0:
            st.error("Uploaded file is empty or corrupted.")
            st.stop()
            
        st.audio(uploaded_file)
        
        process_btn_disabled = not uploaded_file or not deepgram_key or not groq_key
        
        if st.button("Process Meeting", disabled=process_btn_disabled, type="primary"):
            st.session_state["raw_transcript"] = None
            st.session_state["refined_transcript"] = None
            st.session_state["markdown_minutes"] = None
            st.session_state["json_minutes"] = None
            
            audio_bytes = uploaded_file.read()
            mime_type = get_audio_mime_type(uploaded_file.name)
            
            with st.status("Processing Meeting...", expanded=True) as status:
                try:
                    # Stage 1
                    st.write("Stage 1: Transcribing audio with Deepgram...")
                    start_t = time.time()
                    raw_transcript = process_stage_1_deepgram(audio_bytes, mime_type, deepgram_key)
                    if not raw_transcript:
                        raise ValueError("No transcript generated.")
                    st.session_state["raw_transcript"] = raw_transcript
                    st.write(f"✓ Transcription complete ({time.time() - start_t:.1f}s)")
                    
                    # Stage 2
                    st.write("Stage 2: Refining transcript with Groq...")
                    start_t = time.time()
                    refined_transcript = process_stage_2_refine_transcript(raw_transcript, groq_key)
                    st.session_state["refined_transcript"] = refined_transcript
                    st.write(f"✓ Refinement complete ({time.time() - start_t:.1f}s)")
                    
                    # Stage 3
                    st.write("Stage 3: Generating meeting minutes...")
                    start_t = time.time()
                    markdown_minutes, json_minutes = process_stage_3_meeting_minutes(refined_transcript, groq_key)
                    st.session_state["markdown_minutes"] = markdown_minutes
                    st.session_state["json_minutes"] = json_minutes
                    st.write(f"✓ Minutes generation complete ({time.time() - start_t:.1f}s)")
                    
                    status.update(label="Processing Complete!", state="complete", expanded=False)
                    st.success("Successfully processed the meeting!")
                    
                except Exception as e:
                    status.update(label="Processing Failed", state="error")
                    st.error(f"Error during processing: {str(e)}")
                    st.stop()
                    
    st.divider()

    # Results Display
    if st.session_state.get("markdown_minutes") is not None:
        tab1, tab2, tab3, tab4 = st.tabs([
            "Raw Transcript", 
            "Refined Transcript", 
            "Meeting Minutes", 
            "JSON Output"
        ])
        
        with tab1:
            st.text_area("Raw Transcript Content", st.session_state["raw_transcript"], height=400)
            st.download_button("Download Raw Transcript", st.session_state["raw_transcript"], file_name="raw_transcript.txt")
            
        with tab2:
            st.text_area("Refined Transcript Content", st.session_state["refined_transcript"], height=400)
            st.download_button("Download Refined Transcript", st.session_state["refined_transcript"], file_name="refined_transcript.txt")
            
        with tab3:
            st.markdown(st.session_state["markdown_minutes"])
            st.download_button("Download Meeting Minutes", st.session_state["markdown_minutes"], file_name="meeting_minutes.md")
            
        with tab4:
            st.json(st.session_state["json_minutes"])
            st.download_button("Download JSON Output", st.session_state["json_minutes"], file_name="meeting_minutes.json")

if __name__ == "__main__":
    main()
