import streamlit as st
from datetime import datetime

st.set_page_config(page_title="온라인 탐정게임", layout="wide")

# -----------------------------
# 기본 데이터
# -----------------------------
CHARACTERS = [
    {"id": "char1", "name": "등장인물 1", "image": None},
    {"id": "char2", "name": "등장인물 2", "image": None},
    {"id": "char3", "name": "등장인물 3", "image": None},
    {"id": "char4", "name": "등장인물 4", "image": None},
    {"id": "char5", "name": "등장인물 5", "image": None},
]

CASE_SUMMARY = """
어느 날, 한 사건이 발생했다.
플레이어는 다섯 명의 등장인물을 심문하며 단서를 모아야 한다.
각 인물과의 대화 내용은 저장되며, 이를 바탕으로 진실에 가까워질 수 있다.
"""

# -----------------------------
# 세션 상태 초기화
# -----------------------------
def init_session_state():
    defaults = {
        "page": "start",              # start -> opening -> main
        "day": 1,
        "selected_character": None,
        "game_started": False,
        "chat_logs": {},               # {char_id: [{role: 'user'|'assistant', content: str, time: str}]}
        "game_over": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    for character in CHARACTERS:
        if character["id"] not in st.session_state["chat_logs"]:
            st.session_state["chat_logs"][character["id"]] = []


def reset_game():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()


init_session_state()

# -----------------------------
# 유틸 함수
# -----------------------------
def get_character_by_id(char_id):
    for character in CHARACTERS:
        if character["id"] == char_id:
            return character
    return None


def add_message(char_id, role, content):
    st.session_state["chat_logs"][char_id].append(
        {
            "role": role,
            "content": content,
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    )


def mock_character_reply(user_input, char_name):
    return f"[{char_name}]의 임시 응답입니다. \"{user_input}\"에 대한 답변은 나중에 ChatGPT API와 연결할 수 있습니다."


# -----------------------------
# 사이드바
# -----------------------------
def render_sidebar():
    with st.sidebar:
        st.title("등장인물")
        st.caption("인물을 선택하면 해당 인물과의 대화창이 열립니다.")

        for character in CHARACTERS:
            st.markdown("---")
            if character["image"]:
                st.image(character["image"], use_container_width=True)
            else:
                st.markdown(
                    """
                    <div style="
                        width:100%;
                        height:140px;
                        border:1px dashed #999;
                        border-radius:12px;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        background-color:#f6f6f6;
                        color:#666;
                        font-size:14px;
                    ">
                        초상화 자리
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.button(character["name"], key=f"select_{character['id']}", use_container_width=True):
                st.session_state["selected_character"] = character["id"]
                st.session_state["page"] = "main"

        st.markdown("---")
        if st.button("게임 초기화", use_container_width=True):
            reset_game()
            st.rerun()


# -----------------------------
# 시작 화면
# -----------------------------
def render_start_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 온라인 탐정게임")
        st.markdown(
            """
            <div style="
                width:100%;
                height:240px;
                border:2px dashed #999;
                border-radius:16px;
                display:flex;
                align-items:center;
                justify-content:center;
                background-color:#fafafa;
                color:#666;
                font-size:18px;
                margin-top:20px;
                margin-bottom:20px;
            ">
                로고 이미지 자리
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("게임시작", use_container_width=True):
            st.session_state["page"] = "opening"
            st.session_state["game_started"] = True
            st.rerun()


# -----------------------------
# 오프닝 화면
# -----------------------------
def render_opening_page():
    st.markdown("## 사건 오프닝")

    st.markdown(
        """
        <div style="
            width:100%;
            height:280px;
            border:2px dashed #999;
            border-radius:16px;
            display:flex;
            align-items:center;
            justify-content:center;
            background-color:#fafafa;
            color:#666;
            font-size:18px;
            margin-top:10px;
            margin-bottom:20px;
        ">
            오프닝 이미지 자리
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write(CASE_SUMMARY)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("메인 화면으로 이동", use_container_width=True):
            st.session_state["page"] = "main"
            st.rerun()


# -----------------------------
# 메인 화면
# -----------------------------
def render_main_page():
    top_left, top_right = st.columns([6, 1])
    with top_right:
        st.markdown(f"### {st.session_state['day']}일차")

    selected_character_id = st.session_state["selected_character"]

    if not selected_character_id:
        st.markdown("## 메인 화면")
        st.info("왼쪽 사이드바에서 심문할 등장인물을 선택하세요.")
        st.markdown("\n")
        st.button("범인 지목", disabled=True, use_container_width=False)
        return

    character = get_character_by_id(selected_character_id)
    st.markdown(f"## {character['name']} 심문")

    # 이전 대화 표시
    chat_container = st.container(border=True)
    with chat_container:
        if not st.session_state["chat_logs"][selected_character_id]:
            st.caption("아직 대화 기록이 없습니다.")
        else:
            for msg in st.session_state["chat_logs"][selected_character_id]:
                with st.chat_message("user" if msg["role"] == "user" else "assistant"):
                    st.write(msg["content"])
                    st.caption(msg["time"])

    # 새 메시지 입력
    user_input = st.chat_input(f"{character['name']}에게 질문하기")
    if user_input:
        add_message(selected_character_id, "user", user_input)
        reply = mock_character_reply(user_input, character["name"])
        add_message(selected_character_id, "assistant", reply)
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, _, right_col = st.columns([5, 2, 1])
    with right_col:
        st.button("범인 지목", use_container_width=True)


# -----------------------------
# 렌더링
# -----------------------------
render_sidebar()

if st.session_state["page"] == "start":
    render_start_page()
elif st.session_state["page"] == "opening":
    render_opening_page()
else:
    render_main_page()
