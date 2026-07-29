from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import (
    json_text,
    now_iso,
    run_model_tool_loop,
    safe_slug,
    trim_history,
    write_transcript,
)
from env_loader import load_lab_env
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"
RUNS_DIR = ROOT / "runs"
load_lab_env(ROOT)

PROVIDERS = ["openrouter", "gemini", "openai", "anthropic"]
SCENARIOS = {
    "Research news": "Tin tức AI hôm nay có gì nổi bật? Tóm tắt 5 ý chính kèm nguồn.",
    "Missing info": "Tóm tắt 5 tweet mới nhất giúp mình.",
    "Follow-up info": "Của Elon Musk nhé.",
    "Sensitive action": "Gửi bản tóm tắt này lên Telegram giúp mình.",
    "Read URL": "Tóm tắt bài này giúp mình: https://openai.com/blog/gpt-5",
}


def init_state() -> None:
    defaults = {
        "messages": [],
        "history": [],
        "turns": [],
        "transcript_path": None,
        "transcript_meta": None,
        "draft": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def latest_run_summaries(limit: int = 4) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(RUNS_DIR.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            summary = data.get("summary", {})
            rows.append({
                "run": path.name,
                "version": data.get("version"),
                "provider": data.get("provider"),
                "accuracy": summary.get("case_accuracy"),
                "measured": summary.get("measured_cases"),
                "provider_errors": summary.get("provider_error_cases"),
            })
        except Exception:
            continue
    return rows


def make_transcript_meta(
    *,
    provider_name: str,
    model: str | None,
    version: str,
    system_prompt_path: Path,
    tools_path: Path,
    history_window: int,
    max_tool_rounds: int,
) -> tuple[dict[str, Any], Path]:
    provider = make_provider(provider_name)
    selected_model = model or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(version, system_prompt_path, tools_path)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version), safe_slug(provider_name), timestamp])
    transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
    meta: dict[str, Any] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": selected_model,
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    return meta, transcript_path


def save_current_transcript() -> None:
    meta = st.session_state.transcript_meta
    path = st.session_state.transcript_path
    if meta and path:
        meta["turns"] = st.session_state.turns
        write_transcript(Path(path), meta)


def reset_chat() -> None:
    st.session_state.messages = []
    st.session_state.history = []
    st.session_state.turns = []
    st.session_state.transcript_path = None
    st.session_state.transcript_meta = None


def run_turn(
    *,
    user_text: str,
    provider_name: str,
    model: str | None,
    version: str,
    system_prompt_path: Path,
    tools_path: Path,
    history_window: int,
    max_tool_rounds: int,
) -> None:
    if not st.session_state.transcript_meta:
        meta, path = make_transcript_meta(
            provider_name=provider_name,
            model=model,
            version=version,
            system_prompt_path=system_prompt_path,
            tools_path=tools_path,
            history_window=history_window,
            max_tool_rounds=max_tool_rounds,
        )
        st.session_state.transcript_meta = meta
        st.session_state.transcript_path = str(path)

    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(provider_name)

    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history, history_window),
        {"role": "user", "content": user_text},
    ]
    turn_record: dict[str, Any] = {
        "turn_index": len(st.session_state.turns) + 1,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    try:
        result = run_model_tool_loop(
            provider=provider,
            messages=messages,
            tools=openai_tools,
            model=model or None,
            max_tool_rounds=max_tool_rounds,
        )
        turn_record.update(result)
        assistant_text = result["assistant_text"]
        st.session_state.history.append({"role": "user", "content": user_text})
        st.session_state.history.append({"role": "assistant", "content": assistant_text})
        st.session_state.messages.append({"role": "user", "content": user_text})
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_text,
            "turn": turn_record,
        })
    except Exception as exc:
        turn_record.update({
            "status": "provider_error",
            "error": f"{type(exc).__name__}: {str(exc)}",
        })
        st.session_state.messages.append({"role": "user", "content": user_text})
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"Provider error: {turn_record['error']}",
            "turn": turn_record,
        })

    turn_record["ended_at"] = now_iso()
    st.session_state.turns.append(turn_record)
    save_current_transcript()


def render_tool_trace(turn: dict[str, Any]) -> None:
    rounds = turn.get("rounds") or []
    if not rounds:
        if turn.get("error"):
            st.error(turn["error"])
        return

    for round_record in rounds:
        label = f"Round {round_record.get('round')} · {len(round_record.get('tool_calls') or [])} tool call(s)"
        with st.expander(label, expanded=False):
            calls = round_record.get("tool_calls") or []
            results = round_record.get("tool_results") or []
            if round_record.get("assistant_text"):
                st.caption("Assistant draft")
                st.write(round_record["assistant_text"])
            if calls:
                st.caption("Tool calls")
                st.json(calls, expanded=False)
            if results:
                st.caption("Tool results")
                st.json(results, expanded=False)


def main() -> None:
    st.set_page_config(page_title="Research Agent Demo", page_icon="🔎", layout="wide")
    init_state()

    st.title("Research Agent Demo")

    with st.sidebar:
        st.header("Run Config")
        provider_name = st.selectbox("Provider", PROVIDERS, index=0)
        version = st.text_input("Version", value="v3")
        model = st.text_input("Model override", value="")
        history_window = st.slider("History window", min_value=1, max_value=10, value=5)
        max_tool_rounds = st.slider("Max tool rounds", min_value=1, max_value=6, value=4)
        system_prompt_path = st.text_input("System prompt", value=str(ARTIFACTS_DIR / "system_prompt.md"))
        tools_path = st.text_input("Tools YAML", value=str(ARTIFACTS_DIR / "tools.yaml"))

        artifact = build_artifact_version(version, Path(system_prompt_path), Path(tools_path))
        st.caption("Artifact")
        st.code(artifact.artifact_version)

        if st.button("New transcript", use_container_width=True):
            reset_chat()
            st.rerun()

        if st.session_state.transcript_path:
            st.caption("Transcript")
            st.code(st.session_state.transcript_path)

        summaries = latest_run_summaries()
        if summaries:
            st.divider()
            st.subheader("Recent Runs")
            st.dataframe(summaries, hide_index=True, use_container_width=True)

    st.caption("Use the preset scenarios for rehearsal, then inspect the tool trace and transcript evidence.")

    cols = st.columns(len(SCENARIOS))
    for index, (label, prompt) in enumerate(SCENARIOS.items()):
        if cols[index].button(label, use_container_width=True):
            st.session_state.draft = prompt
            st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if message["role"] == "assistant" and message.get("turn"):
                render_tool_trace(message["turn"])

    with st.form("chat_form", clear_on_submit=True):
        user_text = st.text_area("Message", value=st.session_state.draft, height=90)
        submitted = st.form_submit_button("Send", use_container_width=True)
        if submitted and user_text.strip():
            st.session_state.draft = ""
            run_turn(
                user_text=user_text.strip(),
                provider_name=provider_name,
                model=model.strip() or None,
                version=version,
                system_prompt_path=Path(system_prompt_path),
                tools_path=Path(tools_path),
                history_window=history_window,
                max_tool_rounds=max_tool_rounds,
            )
            st.rerun()

    if st.session_state.transcript_path and Path(st.session_state.transcript_path).exists():
        transcript_text = Path(st.session_state.transcript_path).read_text(encoding="utf-8")
        st.download_button(
            "Download transcript JSON",
            data=transcript_text,
            file_name=Path(st.session_state.transcript_path).name,
            mime="application/json",
            use_container_width=True,
        )

    with st.expander("Current transcript preview", expanded=False):
        st.code(json_text(st.session_state.transcript_meta or {}, max_chars=30000), language="json")


if __name__ == "__main__":
    main()
