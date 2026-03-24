import streamlit as st
from datetime import datetime

st.set_page_config(page_title="온라인 탐정게임", layout="wide")

# =====================================================
# 기본 데이터
# =====================================================
CHARACTERS = [
    {"id": "char1", "name": "등장인물 1", "image": None, "is_culprit": False},
    {"id": "char2", "name": "등장인물 2", "image": None, "is_culprit": False},
    {"id": "char3", "name": "등장인물 3", "image": None, "is_culprit": True},
    {"id": "char4", "name": "등장인물 4", "image": None, "is_culprit": False},
    {"id": "char5", "name": "등장인물 5", "image": None, "is_culprit": False},
]

CASE_SUMMARY = """
어느 날, 한 사건이 발생했다.
플레이어는 다섯 명의 등장인물을 심문하며 단서를 모아야 한다.
각 인물과의 대화 내용은 저장되며, 이를 바탕으로 진실에 가까워질 수 있다.
"""

# 실제 게임에서는 사건별 핵심 이유 키워드를 바꿔서 사용
CORRECT_REASON_KEYWORDS = ["usb", "거짓말", "알리바이"]

# =====================================================
# 세션 상태
# =====================================================
SESSION_DEFAULTS = {
    "page": "start",                  # start -> opening -> main -> accuse -> result
    "day": 1,
    "selected_character": None,
    "game_started": False,
    "game_over": False,
    "chat_logs": {},                   # {char_id: [{role, content, time}]}
    "chat_counts": {},                 # {char_id: int}
    "total_interrogations_used": 0,
    "max_total_interrogations": 10,
    "current_questions_used": 0,
    "max_questions_per_interrogation": 3,
    "interrogation_active": False,
    "accused_character": None,
    "accusation_reason": "",
    "accusation_result": None,         # success / fail
    "result_message": "",
}


def init_session_state():
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            if isinstance(value, dict):
                st.session_state[key] = {}
            else:
                st.session_state[key] = value

    initialize_character_states()



def initialize_character_states():
    for character in CHARACTERS:
        char_id = character["id"]

        if char_id not in st.session_state["chat_logs"]:
            st.session_state["chat_logs"][char_id] = []

        if char_id not in st.session_state["chat_counts"]:
            st.session_state["chat_counts"][char_id] = 0



def clear_all_chat_logs():
    for character in CHARACTERS:
        char_id = character["id"]
        st.session_state["chat_logs"][char_id] = []
        st.session_state["chat_counts"][char_id] = 0



def reset_game():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()


# 단 한 번만 호출
init_session_state()

# =====================================================
# 유틸 함수
# =====================================================
def get_character_by_id(char_id):
    for character in CHARACTERS:
        if character["id"] == char_id:
            return character
    return None



def add_message(char_id, role, content):
    message = {
        "role": role,
        "content": content,
        "time": datetime.now().strftime("%H:%M:%S"),
    }
    st.session_state["chat_logs"][char_id].append(message)
    st.session_state["chat_counts"][char_id] += 1



def get_chat_log(char_id):
    return st.session_state["chat_logs"].get(char_id, [])



def get_chat_count(char_id):
    return st.session_state["chat_counts"].get(char_id, 0)



def mock_character_reply(user_input, char_name):
    return (
        f"[{char_name}]의 임시 응답입니다. "
        f"'{user_input}'에 대한 실제 답변은 나중에 ChatGPT API와 연결하면 됩니다."
    )



def can_start_new_interrogation():
    return (
        st.session_state["total_interrogations_used"]
        < st.session_state["max_total_interrogations"]
    )



def start_interrogation(char_id):
    if not can_start_new_interrogation():
        return False

    st.session_state["selected_character"] = char_id
    st.session_state["interrogation_active"] = True
    st.session_state["current_questions_used"] = 0
    st.session_state["total_interrogations_used"] += 1
    st.session_state["day"] = st.session_state["total_interrogations_used"]
    return True



def end_interrogation():
    st.session_state["selected_character"] = None
    st.session_state["interrogation_active"] = False
    st.session_state["current_questions_used"] = 0



def open_accusation_page():
    st.session_state["selected_character"] = None
    st.session_state["interrogation_active"] = False
    st.session_state["current_questions_used"] = 0
    st.session_state["accused_character"] = None
    st.session_state["accusation_reason"] = ""
    st.session_state["accusation_result"] = None
    st.session_state["result_message"] = ""
    st.session_state["page"] = "accuse"



def is_reason_correct(reason_text):
    normalized = reason_text.strip().lower()
    if not normalized:
        return False

    matched_count = 0
    for keyword in CORRECT_REASON_KEYWORDS:
        if keyword.lower() in normalized:
            matched_count += 1

    return matched_count >= 1



def judge_accusation():
    accused_id = st.session_state["accused_character"]
    reason = st.session_state["accusation_reason"]
    character = get_character_by_id(accused_id)

    if character is None:
        st.session_state["accusation_result"] = "fail"
        st.session_state["result_message"] = "지목한 인물 정보를 찾을 수 없습니다."
        st.session_state["page"] = "result"
        return

    culprit_correct = character["is_culprit"]
    reason_correct = is_reason_correct(reason)

    if culprit_correct and reason_correct:
        st.session_state["accusation_result"] = "success"
        st.session_state["result_message"] = (
            "...그래, 더는 숨길 수 없겠네. 네가 말한 이유가 맞아. "
            "내가 그 사건의 범인이야."
        )
        st.session_state["game_over"] = True
    else:
        st.session_state["accusation_result"] = "fail"
        st.session_state["result_message"] = (
            "아니야, 난 억울해. 네 추리는 틀렸어. "
            "그 이유만으로 날 범인이라고 할 수는 없어."
        )

    st.session_state["page"] = "result"



def render_image_placeholder(text, height=200):
    st.markdown(
        f"""
        <div style="
            width:100%;
            height:{height}px;
            border:2px dashed #999;
            border-radius:16px;
            display:flex;
            align-items:center;
            justify-content:center;
            background-color:#fafafa;
            color:#666;
            font-size:18px;
            text-align:center;
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_character_image(character, height=240, placeholder_text="초상화 자리"):
    if character and character["image"]:
        st.image(character["image"], use_container_width=True)
    else:
        render_image_placeholder(placeholder_text, height=height)


# =====================================================
# 사이드바
# =====================================================
def render_sidebar():
    with st.sidebar:
        st.title("등장인물")

        interrogation_enabled = st.session_state["page"] == "main"
        interrogation_active = st.session_state["interrogation_active"]
        no_more_turns = not can_start_new_interrogation()

        if interrogation_enabled:
            if interrogation_active:
                st.caption("현재 심문이 진행 중입니다. 질문 3개를 모두 사용한 뒤 돌아가기를 눌러주세요.")
            elif no_more_turns:
                st.caption("모든 심문 기회를 사용했습니다. 이제 범인을 지목할 수 있습니다.")
            else:
                st.caption("인물을 선택하면 심문이 시작됩니다.")
        else:
            st.caption("게임 시작 후 메인 화면에서 심문할 수 있습니다.")

        st.markdown(
            f"**심문 횟수:** {st.session_state['total_interrogations_used']} / {st.session_state['max_total_interrogations']}"
        )

        for character in CHARACTERS:
            st.markdown("---")
            render_character_image(character, height=140, placeholder_text="초상화 자리")

            button_disabled = (
                (not interrogation_enabled)
                or interrogation_active
                or no_more_turns
            )

            if st.button(
                character["name"],
                key=f"select_{character['id']}",
                use_container_width=True,
                disabled=button_disabled,
            ):
                started = start_interrogation(character["id"])
                if started:
                    st.rerun()

        st.markdown("---")
        if st.button("게임 초기화", use_container_width=True):
            reset_game()
            st.rerun()


# =====================================================
# 시작 화면
# =====================================================
def render_start_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("## 온라인 탐정게임")
        render_image_placeholder("로고 이미지 자리", height=240)

        if st.button("게임시작", use_container_width=True):
            st.session_state["page"] = "opening"
            st.session_state["game_started"] = True
            st.rerun()


# =====================================================
# 오프닝 화면
# =====================================================
def render_opening_page():
    st.markdown("## 사건 오프닝")
    render_image_placeholder("오프닝 이미지 자리", height=280)
    st.write(CASE_SUMMARY)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("광장으로 이동", use_container_width=True):
            st.session_state["page"] = "main"
            st.rerun()


# =====================================================
# 메인 화면
# =====================================================
def render_main_page():
    header_left, header_right = st.columns([6, 1])
    with header_right:
        used = st.session_state["total_interrogations_used"]
        max_used = st.session_state["max_total_interrogations"]
        st.markdown(f"### {used}일차")
        st.caption(f"심문 {used}/{max_used}")

    selected_character_id = st.session_state["selected_character"]

    if not selected_character_id:
        st.markdown("## 광장")
        remaining = (
            st.session_state["max_total_interrogations"]
            - st.session_state["total_interrogations_used"]
        )
        st.info(f"왼쪽 사이드바에서 심문할 등장인물을 선택하세요. 남은 심문 횟수: {remaining}회")

        _, _, button_col = st.columns([5, 2, 1])
        with button_col:
            if st.button("범인 지목", use_container_width=True):
                open_accusation_page()
                st.rerun()
        return

    character = get_character_by_id(selected_character_id)
    if character is None:
        st.error("선택한 등장인물 정보를 찾을 수 없습니다.")
        return

    st.markdown(f"## {character['name']} 심문")

    left_col, right_col = st.columns([1, 2])

    with left_col:
        render_character_image(character, height=360, placeholder_text="선택한 인물의 초상화 자리")
        st.caption(f"저장된 메시지 수: {get_chat_count(selected_character_id)}")
        st.caption(
            f"이번 심문 질문 수: {st.session_state['current_questions_used']} / {st.session_state['max_questions_per_interrogation']}"
        )

    with right_col:
        chat_container = st.container(border=True)
        with chat_container:
            chat_log = get_chat_log(selected_character_id)

            if not chat_log:
                st.caption("아직 대화 기록이 없습니다.")
            else:
                for msg in chat_log:
                    with st.chat_message(msg["role"]):
                        st.write(msg["content"])
                        st.caption(msg["time"])

        questions_used = st.session_state["current_questions_used"]
        max_questions = st.session_state["max_questions_per_interrogation"]
        interrogation_finished = questions_used >= max_questions

        if interrogation_finished:
            st.warning("이번 심문에서는 질문 3개를 모두 사용했습니다. 돌아가기를 눌러 메인 화면으로 이동하세요.")
            col_back, col_accuse = st.columns(2)
            with col_back:
                if st.button("돌아가기", use_container_width=True):
                    end_interrogation()
                    st.rerun()
            with col_accuse:
                if st.button("범인 지목", key="accuse_from_chat", use_container_width=True):
                    open_accusation_page()
                    st.rerun()
        else:
            user_input = st.chat_input(
                f"{character['name']}에게 질문하기 ({questions_used + 1}/{max_questions})"
            )
            if user_input:
                add_message(selected_character_id, "user", user_input)
                reply = mock_character_reply(user_input, character["name"])
                add_message(selected_character_id, "assistant", reply)
                st.session_state["current_questions_used"] += 1
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, _, button_col = st.columns([5, 2, 1])
    with button_col:
        if st.button("범인 지목", key="accuse_bottom", use_container_width=True):
            open_accusation_page()
            st.rerun()


# =====================================================
# 범인 지목 화면
# =====================================================
def render_accusation_page():
    st.markdown("## 범인 지목")
    st.write("등장인물을 선택하고, 범인이라고 생각하는 이유를 작성하세요.")

    if st.button("광장으로 돌아가기"):
        st.session_state["page"] = "main"
        st.rerun()

    st.markdown("### 1. 지목할 등장인물 선택")
    cols = st.columns(len(CHARACTERS))

    for idx, character in enumerate(CHARACTERS):
        with cols[idx]:
            render_character_image(character, height=170, placeholder_text="초상화 자리")
            selected = st.session_state["accused_character"] == character["id"]
            label = f"선택됨: {character['name']}" if selected else character["name"]
            if st.button(label, key=f"accuse_select_{character['id']}", use_container_width=True):
                st.session_state["accused_character"] = character["id"]
                st.rerun()

    selected_character = get_character_by_id(st.session_state["accused_character"])
    if selected_character:
        st.success(f"현재 지목 대상: {selected_character['name']}")

    st.markdown("### 2. 지목 이유 작성")
    reason = st.text_area(
        "왜 이 인물이 범인이라고 생각하나요?",
        value=st.session_state["accusation_reason"],
        height=160,
        placeholder="증거, 모순, 알리바이 문제 등을 적어보세요.",
    )
    st.session_state["accusation_reason"] = reason

    submit_disabled = not st.session_state["accused_character"] or not reason.strip()
    if st.button("판정 받기", use_container_width=True, disabled=submit_disabled):
        judge_accusation()
        st.rerun()


# =====================================================
# 판정 화면
# =====================================================
def render_result_page():
    accused_character = get_character_by_id(st.session_state["accused_character"])
    if accused_character is None:
        st.error("판정할 인물 정보가 없습니다.")
        return

    is_success = st.session_state["accusation_result"] == "success"

    banner_text = "범인 지목 성공!" if is_success else "실패.."
    banner_color = "#e8f7ec" if is_success else "#fdecec"
    banner_text_color = "#1f7a3d" if is_success else "#b42318"
    banner_border = "#8fd19e" if is_success else "#f5a3a3"

    st.markdown(
        f"""
        <div style="
            width:100%;
            text-align:center;
            padding:22px 16px;
            margin:10px 0 24px 0;
            border-radius:18px;
            background-color:{banner_color};
            border:2px solid {banner_border};
            color:{banner_text_color};
            font-size:36px;
            font-weight:800;
        ">
            {banner_text}
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1, 2])

    with left_col:
        render_character_image(accused_character, height=320, placeholder_text="지목한 인물의 초상화 자리")
        st.markdown(f"### {accused_character['name']}")

    with right_col:
        st.markdown("### 제출한 지목 이유")
        st.info(st.session_state["accusation_reason"])

        st.markdown("### 인물의 응답")
        st.write(st.session_state["result_message"])

    st.markdown("<br>", unsafe_allow_html=True)

    if is_success:
        _, center_col, _ = st.columns([1, 1, 1])
        with center_col:
            if st.button("게임 처음으로", use_container_width=True):
                reset_game()
                st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("다시 지목하기", use_container_width=True):
                st.session_state["page"] = "accuse"
                st.rerun()
        with col2:
            if st.button("메인 화면으로 돌아가기", use_container_width=True):
                st.session_state["page"] = "main"
                st.rerun()


# =====================================================
# 렌더링
# =====================================================
render_sidebar()

if st.session_state["page"] == "start":
    render_start_page()
elif st.session_state["page"] == "opening":
    render_opening_page()
elif st.session_state["page"] == "main":
    render_main_page()
elif st.session_state["page"] == "accuse":
    render_accusation_page()
else:
    render_result_page()
