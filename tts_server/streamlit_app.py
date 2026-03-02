#!/usr/bin/env python3
"""
TTS Server Streamlit Test App
GD Voice Clone - REST API + WebSocket 스트리밍 + 음성통화 테스트
"""

import streamlit as st
import requests
import json
import time
import wave
import io
import asyncio
import os
import base64
from typing import Optional

try:
    import websockets
except ImportError:
    st.error("websockets 패키지가 필요합니다: pip install websockets")
    st.stop()

# 페이지 설정
st.set_page_config(
    page_title="GD Voice Clone TTS",
    page_icon="🎤",
    layout="wide",
)

# 상수
SERVER_HOST = os.environ.get("TTS_SERVER_HOST", "localhost")
SAMPLE_RATE_IN = 16000   # STT 입력 (Whisper)
SAMPLE_RATE_OUT = 24000  # TTS 출력




def build_api_url(host: str) -> str:
    """호스트 문자열에서 API URL 생성"""
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    elif "ngrok" in host or ("." in host and not host.replace(".", "").isdigit()):
        return f"https://{host}"
    else:
        return f"http://{host}:5002"


def build_ws_url(host: str) -> str:
    """호스트 문자열에서 WebSocket URL 생성"""
    if host.startswith("http://"):
        return host.replace("http://", "ws://").rstrip("/") + "/ws/tts/stream"
    elif host.startswith("https://"):
        return host.replace("https://", "wss://").rstrip("/") + "/ws/tts/stream"
    elif "ngrok" in host or ("." in host and not host.replace(".", "").isdigit()):
        return f"wss://{host}/ws/tts/stream"
    else:
        return f"ws://{host}:5002/ws/tts/stream"


def check_server_health(host: str) -> dict:
    """서버 상태 확인"""
    try:
        api_url = build_api_url(host)
        response = requests.get(f"{api_url}/api/v1/health", timeout=5)
        return response.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_voices(host: str) -> list:
    """사용 가능한 음성 목록"""
    try:
        api_url = build_api_url(host)
        response = requests.get(f"{api_url}/api/v1/tts/voices", timeout=5)
        data = response.json()
        return data.get("voices", [])
    except Exception:
        return []


def synthesize_rest(
    text: str,
    voice_id: str,
    host: str = "localhost",
    temperature: Optional[float] = None,
    top_k: Optional[int] = None,
    top_p: Optional[float] = None,
    repetition_penalty: Optional[float] = None,
) -> tuple[Optional[bytes], dict]:
    """REST API로 TTS 합성"""
    start_time = time.time()
    api_url = build_api_url(host)

    payload = {"text": text, "voice_id": voice_id}
    if temperature is not None:
        payload["temperature"] = temperature
    if top_k is not None:
        payload["top_k"] = top_k
    if top_p is not None:
        payload["top_p"] = top_p
    if repetition_penalty is not None:
        payload["repetition_penalty"] = repetition_penalty

    try:
        response = requests.post(
            f"{api_url}/api/v1/tts/synthesize",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        elapsed = (time.time() - start_time) * 1000

        if response.status_code == 200:
            audio_duration = float(response.headers.get("X-Audio-Duration", "0"))
            process_time = float(response.headers.get("X-Processing-Time", str(elapsed)))

            return response.content, {
                "success": True,
                "elapsed_ms": elapsed,
                "process_time_ms": process_time,
                "audio_duration": audio_duration,
                "audio_bytes": len(response.content),
            }
        else:
            return None, {
                "success": False,
                "error": response.json().get("message", "Unknown error"),
                "status_code": response.status_code,
            }

    except Exception as e:
        return None, {"success": False, "error": str(e)}


async def synthesize_websocket(text: str, voice_id: str, host: str = "localhost") -> tuple[Optional[bytes], dict]:
    """WebSocket으로 TTS 스트리밍"""
    audio_chunks = []
    metrics = {"success": False, "chunks": 0, "ttfa_ms": None, "total_ms": None}

    start_time = time.time()
    ws_url = build_ws_url(host)

    try:
        async with websockets.connect(ws_url) as ws:
            msg = await ws.recv()
            data = json.loads(msg)
            metrics["client_id"] = data.get("client_id")

            await ws.send(json.dumps({
                "type": "synthesize",
                "text": text,
                "voice_id": voice_id,
            }))

            while True:
                msg = await ws.recv()

                if isinstance(msg, bytes):
                    if metrics["ttfa_ms"] is None:
                        metrics["ttfa_ms"] = (time.time() - start_time) * 1000
                    audio_chunks.append(msg)
                    metrics["chunks"] += 1
                else:
                    data = json.loads(msg)
                    if data["type"] == "end":
                        metrics["success"] = True
                        metrics["total_ms"] = (time.time() - start_time) * 1000
                        metrics["audio_duration"] = data.get("duration", 0)
                        break
                    elif data["type"] == "error":
                        metrics["error"] = data.get("message", "Unknown error")
                        break

        if audio_chunks:
            audio_bytes = b"".join(audio_chunks)
            metrics["audio_bytes"] = len(audio_bytes)
            return audio_bytes, metrics
        else:
            return None, metrics

    except Exception as e:
        metrics["error"] = str(e)
        return None, metrics


def run_websocket_synthesis(text: str, voice_id: str, host: str = "localhost"):
    """WebSocket 합성 실행 (동기 래퍼)"""
    return asyncio.run(synthesize_websocket(text, voice_id, host))


def build_voice_call_ws_url(host: str) -> str:
    """Voice Call WebSocket URL 생성"""
    if host.startswith("http://"):
        return host.replace("http://", "ws://").rstrip("/") + "/ws/voice/call"
    elif host.startswith("https://"):
        return host.replace("https://", "wss://").rstrip("/") + "/ws/voice/call"
    elif "ngrok" in host or ("." in host and not host.replace(".", "").isdigit()):
        return f"wss://{host}/ws/voice/call"
    else:
        return f"ws://{host}:5002/ws/voice/call"


async def voice_call(audio_bytes: bytes, host: str = "localhost", voice_id: str = "gd-default") -> tuple[Optional[bytes], dict]:
    """
    음성통화 WebSocket API 호출

    Args:
        audio_bytes: PCM 16-bit 16kHz 오디오
        host: 서버 호스트
        voice_id: TTS 음성 ID

    Returns:
        (응답 오디오, 메트릭)
    """
    audio_chunks = []
    metrics = {
        "success": False,
        "transcription": "",
        "response_text": "",
        "stt_ms": 0,
        "llm_ttfa_ms": 0,
        "tts_ttfa_ms": 0,
        "total_ms": 0,
    }

    start_time = time.time()
    ws_url = build_voice_call_ws_url(host)

    try:
        async with websockets.connect(ws_url) as ws:
            # 연결 확인
            msg = await ws.recv()
            data = json.loads(msg)
            metrics["client_id"] = data.get("client_id")

            # 오디오 전송 (Base64 인코딩)
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            await ws.send(json.dumps({
                "type": "voice_input",
                "audio": audio_base64,
                "voice_id": voice_id,
            }))

            # 응답 수신
            while True:
                msg = await ws.recv()

                if isinstance(msg, bytes):
                    # TTS 오디오 청크
                    audio_chunks.append(msg)
                else:
                    data = json.loads(msg)
                    msg_type = data.get("type")

                    if msg_type == "transcription":
                        metrics["transcription"] = data.get("text", "")

                    elif msg_type == "response_text":
                        metrics["response_text"] += data.get("text", "")

                    elif msg_type == "response_end":
                        metrics["success"] = True
                        metrics["total_ms"] = (time.time() - start_time) * 1000
                        if data.get("metrics"):
                            metrics.update(data["metrics"])
                        break

                    elif msg_type == "error":
                        metrics["error"] = data.get("message", "Unknown error")
                        break

                    elif msg_type == "interrupted":
                        metrics["interrupted"] = True
                        break

        if audio_chunks:
            audio_bytes_out = b"".join(audio_chunks)
            metrics["audio_bytes"] = len(audio_bytes_out)
            return audio_bytes_out, metrics
        else:
            return None, metrics

    except Exception as e:
        metrics["error"] = str(e)
        return None, metrics


def run_voice_call(audio_bytes: bytes, host: str = "localhost", voice_id: str = "gd-default"):
    """음성통화 실행 (동기 래퍼)"""
    return asyncio.run(voice_call(audio_bytes, host, voice_id))


# === UI ===

st.title("🎤 GD Voice Clone TTS")
st.markdown("G-Dragon 음성 복제 TTS 서버 테스트")

# 사이드바
with st.sidebar:
    st.header("서버 설정")

    if "server_host" not in st.session_state:
        st.session_state["server_host"] = SERVER_HOST

    server_host = st.text_input(
        "TTS 서버 주소",
        value=st.session_state["server_host"],
        help="TTS 서버의 IP 또는 호스트명",
    )

    if server_host != st.session_state["server_host"]:
        st.session_state["server_host"] = server_host
        st.rerun()

    st.caption(f"API: {build_api_url(server_host or 'localhost')}")

    st.divider()
    st.header("서버 상태")

    if st.button("🔄 상태 새로고침"):
        st.rerun()

    health = check_server_health(server_host or "localhost")

    if health.get("status") == "healthy":
        st.success("✅ 서버 연결됨")
        st.json(health)
    else:
        st.error("❌ 서버 연결 실패")
        st.json(health)
        st.warning("서버를 먼저 시작하세요:\n`python main.py`")

# 메인 영역
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎤 GD 음성 복제")
    st.caption("G-Dragon 목소리로 텍스트를 음성으로 변환합니다")

    # 텍스트 입력
    text_input = st.text_area(
        "텍스트 입력",
        value="안녕하세요, 저는 지드래곤입니다. 오늘도 좋은 하루 보내세요.",
        height=100,
        max_chars=500,
    )

    # 음성 선택
    voices = get_voices(st.session_state.get("server_host", "localhost"))
    voice_options = {v["id"]: f"{v['name']} ({v['mode']})" for v in voices}

    if voice_options:
        selected_voice = st.selectbox(
            "음성 선택",
            options=list(voice_options.keys()),
            format_func=lambda x: voice_options[x],
        ) or "gd-default"
    else:
        selected_voice = "gd-default"
        st.warning("음성 목록을 불러올 수 없습니다. 기본값 사용")

    # 전송 방식
    mode = st.radio(
        "전송 방식",
        ["REST API", "WebSocket Streaming"],
        horizontal=True,
    )

    # 고급 설정
    with st.expander("🎛️ 음성 품질 설정", expanded=False):
        st.caption("낮은 Temperature = 더 일관된 목소리 (GD 음색 유지에 중요)")

        col_temp, col_topk = st.columns(2)
        with col_temp:
            gen_temperature = st.slider(
                "Temperature",
                min_value=0.1,
                max_value=1.5,
                value=0.6,
                step=0.1,
                help="낮을수록 일관성 ↑ (0.5~0.7 권장)",
            )
        with col_topk:
            gen_top_k = st.slider(
                "Top-K",
                min_value=10,
                max_value=100,
                value=50,
                step=10,
                help="높을수록 다양성 ↑",
            )

        col_topp, col_rep = st.columns(2)
        with col_topp:
            gen_top_p = st.slider(
                "Top-P (Nucleus)",
                min_value=0.5,
                max_value=1.0,
                value=0.9,
                step=0.05,
                help="0.9~0.95 권장",
            )
        with col_rep:
            gen_repetition_penalty = st.slider(
                "Repetition Penalty",
                min_value=1.0,
                max_value=1.5,
                value=1.1,
                step=0.05,
                help="반복 억제 (1.0~1.2 권장)",
            )

        use_custom_params = st.checkbox("커스텀 파라미터 사용", value=False)

    # 합성 버튼
    if st.button("🎙️ 합성 시작", type="primary", use_container_width=True):
        if not text_input.strip():
            st.error("텍스트를 입력하세요")
        else:
            with st.spinner("합성 중..."):
                current_host = st.session_state.get("server_host", "localhost")

                if use_custom_params:
                    temp = gen_temperature
                    topk = gen_top_k
                    topp = gen_top_p
                    rep = gen_repetition_penalty
                else:
                    temp = topk = topp = rep = None

                if mode == "REST API":
                    audio_bytes, metrics = synthesize_rest(
                        text_input,
                        selected_voice,
                        current_host,
                        temperature=temp,
                        top_k=topk,
                        top_p=topp,
                        repetition_penalty=rep,
                    )
                else:
                    audio_bytes, metrics = run_websocket_synthesis(
                        text_input, selected_voice, current_host
                    )

            # 결과 저장
            st.session_state["last_audio"] = audio_bytes
            st.session_state["last_metrics"] = metrics
            st.session_state["audio_timestamp"] = str(int(time.time() * 1000))

            # UI 강제 갱신
            st.rerun()

with col2:
    st.header("결과")

    if "last_metrics" in st.session_state:
        metrics = st.session_state["last_metrics"]

        if metrics.get("success"):
            st.success("✅ 합성 성공")

            col_a, col_b = st.columns(2)
            with col_a:
                if metrics.get("ttfa_ms"):
                    st.metric("TTFA", f"{metrics['ttfa_ms']:.0f}ms")
                elif metrics.get("process_time_ms"):
                    st.metric("처리 시간", f"{metrics['process_time_ms']:.0f}ms")

            with col_b:
                if metrics.get("audio_duration"):
                    st.metric("오디오 길이", f"{metrics['audio_duration']:.2f}s")

            if metrics.get("chunks"):
                st.metric("청크 수", metrics["chunks"])

            if metrics.get("audio_bytes"):
                st.metric("오디오 크기", f"{metrics['audio_bytes']:,} bytes")

            with st.expander("상세 메트릭"):
                st.json(metrics)
        else:
            st.error(f"❌ 합성 실패: {metrics.get('error', 'Unknown')}")
            st.json(metrics)

    # 오디오 플레이어
    if "last_audio" in st.session_state and st.session_state["last_audio"]:
        st.subheader("🔊 오디오 재생")

        # WAV 파일 생성
        audio_buffer = io.BytesIO()
        with wave.open(audio_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE_OUT)
            wav.writeframes(st.session_state["last_audio"])

        # st.audio() 네이티브 컴포넌트 사용 (가장 안정적)
        audio_buffer.seek(0)
        st.audio(audio_buffer, format="audio/wav")

        # 다운로드 버튼
        audio_buffer.seek(0)
        st.download_button(
            label="💾 WAV 다운로드",
            data=audio_buffer.getvalue(),
            file_name="gd_tts_output.wav",
            mime="audio/wav",
        )

# === Voice Call 탭 ===
st.divider()
st.subheader("📞 실시간 음성통화")
st.caption("마이크로 말하면 GD가 대답합니다 (STT → LLM → TTS)")

# 음성 녹음 UI
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode
    import av
    import numpy as np
    from collections import deque

    # 오디오 버퍼
    if "voice_buffer" not in st.session_state:
        st.session_state["voice_buffer"] = deque(maxlen=100)

    class AudioProcessor:
        """오디오 프로세서 - 마이크 입력 캡처"""
        def __init__(self):
            self.audio_frames = []

        def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
            # PCM 데이터 추출
            audio = frame.to_ndarray()
            st.session_state["voice_buffer"].append(audio.tobytes())
            return frame

    col_voice1, col_voice2 = st.columns([2, 1])

    with col_voice1:
        # WebRTC 스트리머 (마이크 입력)
        webrtc_ctx = webrtc_streamer(
            key="voice-call",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=1024,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={"audio": True, "video": False},
        )

        if st.button("🎤 음성 전송", type="primary", use_container_width=True):
            if "voice_buffer" in st.session_state and st.session_state["voice_buffer"]:
                # 버퍼 합치기
                audio_data = b"".join(st.session_state["voice_buffer"])
                st.session_state["voice_buffer"].clear()

                if len(audio_data) > 0:
                    with st.spinner("음성 처리 중..."):
                        current_host = st.session_state.get("server_host", "localhost")
                        voice_id = st.session_state.get("selected_voice", "gd-default")

                        response_audio, metrics = run_voice_call(
                            audio_data,
                            current_host,
                            voice_id,
                        )

                        st.session_state["voice_call_audio"] = response_audio
                        st.session_state["voice_call_metrics"] = metrics

                    st.rerun()
                else:
                    st.warning("녹음된 오디오가 없습니다")
            else:
                st.warning("먼저 마이크로 말씀해주세요")

    with col_voice2:
        st.markdown("**통화 결과**")

        if "voice_call_metrics" in st.session_state:
            metrics = st.session_state["voice_call_metrics"]

            if metrics.get("success"):
                st.success("✅ 응답 완료")

                # 인식된 텍스트
                if metrics.get("transcription"):
                    st.markdown(f"**나:** {metrics['transcription']}")

                # GD 응답
                if metrics.get("response_text"):
                    st.markdown(f"**GD:** {metrics['response_text']}")

                # 메트릭 표시
                with st.expander("상세 메트릭"):
                    st.json(metrics)

            else:
                st.error(f"❌ 실패: {metrics.get('error', 'Unknown')}")

        # 응답 오디오 재생
        if "voice_call_audio" in st.session_state and st.session_state["voice_call_audio"]:
            st.markdown("**🔊 GD 음성 응답:**")

            voice_buffer = io.BytesIO()
            with wave.open(voice_buffer, "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE_OUT)
                wav.writeframes(st.session_state["voice_call_audio"])

            voice_buffer.seek(0)
            st.audio(voice_buffer, format="audio/wav", autoplay=True)

except ImportError:
    st.warning("실시간 음성 녹음을 위해 streamlit-webrtc가 필요합니다")
    st.code("pip install streamlit-webrtc av", language="bash")

    # Fallback: 파일 업로드 방식
    st.markdown("**또는 녹음된 WAV 파일 업로드:**")

    uploaded_audio = st.file_uploader(
        "WAV 파일 선택 (16kHz, mono)",
        type=["wav"],
        key="voice_upload",
    )

    if uploaded_audio is not None:
        # WAV 파일 읽기
        audio_bytes = uploaded_audio.read()

        # PCM 추출 (WAV 헤더 제거)
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
            pcm_data = wav.readframes(wav.getnframes())

        if st.button("📤 음성 전송", type="primary"):
            with st.spinner("음성 처리 중..."):
                current_host = st.session_state.get("server_host", "localhost")
                response_audio, metrics = run_voice_call(
                    pcm_data,
                    current_host,
                    "gd-default",
                )

                st.session_state["voice_call_audio"] = response_audio
                st.session_state["voice_call_metrics"] = metrics

            st.rerun()

    # 결과 표시
    if "voice_call_metrics" in st.session_state:
        metrics = st.session_state["voice_call_metrics"]

        if metrics.get("success"):
            st.success("✅ 응답 완료")
            st.markdown(f"**나:** {metrics.get('transcription', '')}")
            st.markdown(f"**GD:** {metrics.get('response_text', '')}")

            with st.expander("상세 메트릭"):
                st.json(metrics)
        else:
            st.error(f"❌ 실패: {metrics.get('error', 'Unknown')}")

    if "voice_call_audio" in st.session_state and st.session_state["voice_call_audio"]:
        voice_buffer = io.BytesIO()
        with wave.open(voice_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE_OUT)
            wav.writeframes(st.session_state["voice_call_audio"])

        voice_buffer.seek(0)
        st.audio(voice_buffer, format="audio/wav", autoplay=True)

# 하단 정보
st.divider()
_host = st.session_state.get("server_host", "localhost")
st.caption(f"서버: {build_api_url(_host)}")
