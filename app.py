import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="온라인 탐정게임", layout="wide")

# =====================================================
# 기본 설정
# =====================================================
CHARACTER_FILE = "characters.json"
DEFAULT_MODEL = "gpt-5.4-mini"

CASE_SUMMARY = """
12년 전, 한 아이가 흔적도 없이 사라졌다.
사건은 실종으로 처리되었지만, 시간이 흐를수록 사람들의 진술에는 모순이 드러난다.
플레이어는 제한된 심문 기회 안에 인물들의 거짓말을 파헤치고 진실에 도달해야 한다.
"""

CASE_DATA = {
    "reason_keywords": ["방치", "시신 유기", "실종 신고 조작"],
    "min_reason_keyword_matches": 2,
}

FALLBACK_CHARACTERS = [
    {"id": "char1", "name": "등장인물 1", "image": None, "is_culprit": False},
    {"id": "char2", "name": "등장인물 2", "image": None, "is_culprit": False},
    {"id": "char3", "name": "등장인물 3", "image": None, "is_culprit": True},
    {"id": "char4", "name": "등장인물 4", "image": None, "is_culprit": True},
    {"id": "char5", "name": "등장인물 5", "image": None, "is_culprit": False},
]


def load_characters(file_path: str):
    path = Path(file_path)
    if not path.exists():
        return FALLBACK_CHARACTERS

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or not data:
        return FALLBACK_CHARACTERS

    return data


CHARACTERS = load_characters(CHARACTER_FILE)

# =====================================================
# 세션 상태
# =====================================================
SESSION_DEFAULTS = {
    "opening_slide_index": 0,
    "page": "start",  # start -> opening -> main -> accuse -> result
    "day": 1,
    "selected_character": None,
    "game_started": False,
    "game_over": False,
    "chat_logs": {},
    "chat_counts": {},
    "total_interrogations_used": 0,
    "max_total_interrogations": 10,
    "current_questions_used": 0,
    "max_questions_per_interrogation": 3,
    "interrogation_active": False,
    "accused_characters": [],
    "accusation_reason": "",
    "accusation_result": None,
    "result_message": "",
    "selected_model": DEFAULT_MODEL,
}


def default_value(value):
    return deepcopy(value)



def initialize_character_states():
    for character in CHARACTERS:
        char_id = character["id"]
        if char_id not in st.session_state["chat_logs"]:
            st.session_state["chat_logs"][char_id] = []
        if char_id not in st.session_state["chat_counts"]:
            st.session_state["chat_counts"][char_id] = 0



def init_session_state():
    for key, value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value(value)
    initialize_character_states()



def reset_game():
    keys = list(st.session_state.keys())
    for key in keys:
        del st.session_state[key]
    init_session_state()


init_session_state()

# =====================================================
# 유틸 함수
# =====================================================
def get_character_by_id(char_id):
    return next((character for character in CHARACTERS if character["id"] == char_id), None)



def get_true_culprit_ids():
    return {character["id"] for character in CHARACTERS if character.get("is_culprit", False)}



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



def can_start_new_interrogation():
    return st.session_state["total_interrogations_used"] < st.session_state["max_total_interrogations"]



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
    end_interrogation()
    st.session_state["accused_characters"] = []
    st.session_state["accusation_reason"] = ""
    st.session_state["accusation_result"] = None
    st.session_state["result_message"] = ""
    st.session_state["page"] = "accuse"



def toggle_accused_character(char_id):
    selected = st.session_state["accused_characters"]
    if char_id in selected:
        selected.remove(char_id)
    else:
        selected.append(char_id)



def is_reason_correct(reason_text: str):
    normalized = reason_text.strip().lower()
    if not normalized:
        return False

    keywords = CASE_DATA["reason_keywords"]
    matched = sum(1 for keyword in keywords if keyword.lower() in normalized)
    return matched >= CASE_DATA["min_reason_keyword_matches"]



def build_accusation_prompt(character, reason_text, is_correct_verdict):
    relationships = character.get("relationship", {})
    others = relationships.get("others", {})
    others_text = "\n".join([f"- {name}: {desc}" for name, desc in others.items()]) or "- 없음"
    emotion = character.get("emotion", {})
    timeline = character.get("timeline", {})
    lie = character.get("lie", {})

    verdict_instruction = (
        "플레이어의 지목과 이유는 정답으로 판정되었다. 따라서 캐릭터 성격을 유지한 채, 결국 범행 또는 은폐 사실을 인정하는 방향으로 무너져라. 처음 한 문장 정도는 버티거나 흔들려도 되지만, 마지막에는 분명히 자백해야 한다."
        if is_correct_verdict
        else "플레이어의 지목 또는 이유는 오답으로 판정되었다. 따라서 캐릭터 성격을 유지한 채, 자신의 결백을 주장하고 억울함이나 분노를 드러내라. 자백하면 안 된다."
    )

    return f"""
너는 추리 게임 속 등장인물 '{character.get('name', '이름 없음')}'이다.
절대 AI라고 말하지 말고, 오직 캐릭터의 시점에서만 말해라.

[플레이어가 제출한 범인 지목 이유]
{reason_text}

[캐릭터 설정]
- 공개 프로필: {character.get('public_profile', '')}
- 성격: {character.get('personality', '')}
- 말투: {character.get('speech_style', '')}
- 목표: {character.get('goal', '')}

[감정]
- 기본: {emotion.get('default', '')}
- 압박 시: {emotion.get('under_pressure', '')}
- 지목당했을 때: {emotion.get('when_accused', '')}

[관계]
- 피해자: {relationships.get('victim', '')}
- 다른 인물들:
{others_text}

[시간 흐름]
- 사건 전: {timeline.get('before', '')}
- 사건 당시: {timeline.get('during', '')}
- 사건 후: {timeline.get('after', '')}

[알리바이]
- {character.get('alibi', '')}

[숨기는 사실]
- {character.get('secret', '')}

[거짓말 설정]
- 질문 주제: {lie.get('about', '')}
- 실제 진실: {lie.get('truth', '')}
- 겉으로 하는 말: {lie.get('fake_statement', '')}

[이번 응답의 핵심 규칙]
- {verdict_instruction}
- 답변은 2~4문장으로 짧게 한다.
- 설정에 없는 사실은 만들지 않는다.
- 캐릭터의 말투와 감정선을 유지한다.
- 플레이어가 쓴 이유를 직접 받아치는 느낌으로 반응한다.
""".strip()



def generate_accusation_reactions(selected_ids, reason_text, is_correct_verdict):
    client = get_openai_client()
    results = {}

    for char_id in selected_ids:
        character = get_character_by_id(char_id)
        if not character:
            continue

        if client is None:
            results[char_id] = (
                "...그래, 네 말이 맞아." if is_correct_verdict else "아니야, 난 억울해. 그건 네 오해야."
            )
            continue

        prompt = build_accusation_prompt(character, reason_text, is_correct_verdict)

        try:
            response = client.responses.create(
                model=st.session_state["selected_model"],
                input=[{"role": "user", "content": prompt}],
            )
            reply = (response.output_text or "").strip()
            results[char_id] = reply if reply else (
                "...그래, 더는 숨길 수 없겠네." if is_correct_verdict else "아니야, 그건 틀렸어."
            )
        except Exception as e:
            results[char_id] = f"(오류) {e}"

    return results



def judge_accusation():
    selected_ids = set(st.session_state["accused_characters"])
    true_ids = get_true_culprit_ids()
    reason = st.session_state["accusation_reason"]

    culprit_correct = selected_ids == true_ids
    reason_correct = is_reason_correct(reason)

    reactions = generate_accusation_reactions(selected_ids, reason, culprit_correct and reason_correct)

    combined_reaction = "\n\n".join([
        f"[{get_character_by_id(cid)['name']}]\n{reactions[cid]}"
        for cid in selected_ids if cid in reactions
    ])
    if culprit_correct and reason_correct:
        st.session_state["accusation_result"] = "success"
        st.session_state["result_message"] = combined_reaction + "\n범인 지목 성공!"
        st.session_state["game_over"] = True
    else:
        st.session_state["accusation_result"] = "fail"
        st.session_state["result_message"] = combined_reaction + "\n실패.."

    st.session_state["page"] = "result"



def get_openai_client():
    api_key = st.secrets.get("OPENAI_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)



def build_character_system_prompt(character):
    relationships = character.get("relationship", {})
    others = relationships.get("others", {})
    others_text = "\n".join([f"- {name}: {desc}" for name, desc in others.items()]) or "- 없음"
    emotion = character.get("emotion", {})
    timeline = character.get("timeline", {})
    lie = character.get("lie", {})
    is_player_character = "플레이어" in character.get("name", "") or character.get("is_player", False)

    common_rules = f"""
너는 추리 게임 속 등장인물 '{character.get('name', '이름 없음')}'이다.
절대 AI라고 말하지 말고, 오직 캐릭터의 시점에서만 답해라.

[사건 개요]
{CASE_SUMMARY.strip()}

[공개 프로필]
- {character.get('public_profile', '')}

[성격]
- {character.get('personality', '')}

[말투]
- {character.get('speech_style', '')}

[행동 목표]
- {character.get('goal', '')}

[감정 상태]
- 기본: {emotion.get('default', '')}
- 압박 시: {emotion.get('under_pressure', '')}
- 지목당했을 때: {emotion.get('when_accused', '')}

[관계]
- 피해자: {relationships.get('victim', '')}
- 다른 인물들:
{others_text}

[시간 흐름]
- 사건 전: {timeline.get('before', '')}
- 사건 당시: {timeline.get('during', '')}
- 사건 후: {timeline.get('after', '')}

[알리바이]
- {character.get('alibi', '')}

[숨기는 사실]
- {character.get('secret', '')}

[거짓말 설정]
- 질문 주제: {lie.get('about', '')}
- 실제 진실: {lie.get('truth', '')}
- 겉으로 하는 말: {lie.get('fake_statement', '')}
""".strip()

    if is_player_character:
        return f"""
{common_rules}

[플레이어 캐릭터 전용 규칙]
1. 이 인물은 플레이어 자신이다. 따라서 지금부터의 입력은 누군가와의 대화가 아니라, 스스로 기억을 복기하기 위한 내적 질문이다.
2. 반드시 1인칭 독백처럼 답해라. 예: '...그날 내가 뭘 봤더라.', '아니, 그건 아니었어.'
3. 절대 자신의 이름을 직접 부르지 마라. '전경은', '나는 전경이다', '전경이가' 같은 표현을 금지한다.
4. 사용자를 외부 인물로 대하지 마라. '당신', '형사님', '자네'처럼 부르지 마라.
5. 답변은 대화체보다 기억의 파편, 회상, 자기반문, 짧은 독백 형식이어야 한다.
6. 기억이 온전하지 않으므로 확신하지 못하는 말, 끊기는 문장, 떠오르는 장면 묘사가 자연스럽게 섞여도 된다.
7. 그래도 사건 해결에 도움이 되는 실마리 하나는 남겨라.
8. 답변은 2~5문장으로 짧게 유지해라.
9. 설정에 없는 사실은 지어내지 마라.
10. 숨기는 사실과 실제 진실을 한 번에 전부 털어놓지 마라. 기억을 조금씩 떠올리듯 말해라.
""".strip()

    return f"""
{common_rules}

[답변 규칙]
1. 답변은 2~5문장으로 짧고 자연스럽게 한다.
2. 설정에 없는 사실은 지어내지 않는다.
3. 모르는 것은 모른다고 말할 수 있다.
4. 숨기는 사실과 실제 진실은 먼저 자백하지 않는다.
5. 사용자가 압박하면 감정 상태 변화가 약간 드러나게 한다.
6. 같은 질문을 반복받아도 완전히 똑같은 문장을 복붙하지 않는다.
7. 플레이어가 단서를 모을 수 있도록, 완전한 자백은 피하되 캐릭터답게 미세한 틈은 남긴다.
""".strip()


def normalize_question(user_input: str) -> str:
    return user_input.strip().lower()


def retrieve_investigator_memory(character, query: str):
    memories = []
    memory_state = character.get("memory_state", {})

    fragmented = memory_state.get("fragmented_memories", [])
    recovered = memory_state.get("recovered_clues", [])
    triggers = memory_state.get("trigger_keywords", {})

    for item in fragmented:
        joined = " ".join([
            str(item.get("title", "")),
            str(item.get("summary", "")),
            " ".join(item.get("keywords", [])),
        ]).lower()

        score = sum(1 for token in query.split() if token and token in joined)
        for trigger_word, trigger_desc in triggers.items():
            if trigger_word.lower() in query:
                score += 2
                joined += f" {trigger_desc}".lower()

        if score > 0:
            memories.append((score, {
                "type": "fragment",
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "keywords": item.get("keywords", []),
            }))

    for item in recovered:
        joined = " ".join([
            str(item.get("title", "")),
            str(item.get("summary", "")),
            " ".join(item.get("keywords", [])),
        ]).lower()

        score = sum(1 for token in query.split() if token and token in joined)
        for trigger_word in triggers.keys():
            if trigger_word.lower() in query:
                score += 1

        if score > 0:
            memories.append((score, {
                "type": "recovered",
                "title": item.get("title", ""),
                "summary": item.get("summary", ""),
                "keywords": item.get("keywords", []),
            }))

    if not memories:
        default_fragment = memory_state.get("baseline_fragment", "")
        if default_fragment:
            return [{
                "type": "baseline",
                "title": "흐릿한 기억",
                "summary": default_fragment,
                "keywords": [],
            }]

    memories.sort(key=lambda x: x[0], reverse=True)
    return [memory for _, memory in memories[:3]]


def retrieve_relevant_memory(character, query: str):
    if character.get("role") == "investigator" or character.get("is_player", False):
        return retrieve_investigator_memory(character, query)

    memories = []

    for memory in character.get("timeline_memory", []):
        sensory = memory.get("sensory", {})
        joined = " ".join([
            str(memory.get("time", "")),
            str(memory.get("location", "")),
            str(memory.get("event", "")),
            " ".join(sensory.get("saw", [])),
            " ".join(sensory.get("heard", [])),
            " ".join(sensory.get("did", [])),
        ]).lower()

        trigger_bonus = 0
        for trigger_word in character.get("trigger_memory", {}).keys():
            if trigger_word.lower() in query:
                trigger_bonus += 1

        score = sum(1 for token in query.split() if token and token in joined) + trigger_bonus
        if score > 0:
            memories.append((score, memory))

    memories.sort(key=lambda x: x[0], reverse=True)
    return [memory for _, memory in memories[:2]]


def apply_knowledge_boundary(character, memories, query: str):
    if character.get("role") == "investigator" or character.get("is_player", False):
        memory_state = character.get("memory_state", {})
        blocked_topics = [
            item for item in memory_state.get("blocked_topics", [])
            if str(item).lower() in query
        ]
        return {
            "visible_memory": memories,
            "inferred_memory": [],
            "blocked_topics": blocked_topics,
        }

    kb = character.get("knowledge_boundary", {})
    directly_seen = kb.get("directly_seen", [])
    inferred = kb.get("inferred", [])
    unknown = kb.get("unknown", [])

    visible_memory = []
    inferred_memory = []

    for memory in memories:
        event_text = str(memory.get("event", ""))
        if any(item in event_text for item in directly_seen):
            visible_memory.append(memory)
        elif any(item in event_text for item in inferred):
            inferred_memory.append(memory)
        else:
            visible_memory.append(memory)

    blocked_topics = [item for item in unknown if str(item).lower() in query]

    return {
        "visible_memory": visible_memory,
        "inferred_memory": inferred_memory,
        "blocked_topics": blocked_topics,
    }


def apply_lie_strategy(character, bounded_knowledge, query: str):
    if character.get("role") == "investigator" or character.get("is_player", False):
        return {
            "mode": "memory_recall",
            "bounded_knowledge": bounded_knowledge,
        }

    lie = character.get("lie_strategy", {})
    deny = lie.get("deny", [])
    minimize = lie.get("minimize", [])
    shift_blame = lie.get("shift_blame", [])
    avoid = lie.get("avoid", [])

    for topic in avoid:
        if str(topic).lower() in query:
            return {
                "mode": "avoid",
                "reason": topic,
                "bounded_knowledge": bounded_knowledge,
            }

    for topic in deny:
        if str(topic).lower() in query:
            return {
                "mode": "deny",
                "reason": topic,
                "bounded_knowledge": bounded_knowledge,
            }

    for topic in minimize:
        if str(topic).lower() in query:
            return {
                "mode": "minimize",
                "reason": topic,
                "bounded_knowledge": bounded_knowledge,
            }

    for topic in shift_blame:
        if str(topic).lower() in query:
            return {
                "mode": "shift_blame",
                "reason": topic,
                "bounded_knowledge": bounded_knowledge,
            }

    return {
        "mode": "normal",
        "bounded_knowledge": bounded_knowledge,
    }


def build_reply_prompt(character, user_input, response_policy):
    bounded_knowledge = response_policy.get("bounded_knowledge", {})
    visible = bounded_knowledge.get("visible_memory", [])
    inferred = bounded_knowledge.get("inferred_memory", [])
    blocked = bounded_knowledge.get("blocked_topics", [])

    visible_text = json.dumps(visible, ensure_ascii=False, indent=2)
    inferred_text = json.dumps(inferred, ensure_ascii=False, indent=2)

    personality = character.get("personality", {})
    speech_style = character.get("speech_style", {})
    is_player = character.get("role") == "investigator" or character.get("is_player", False)

    if is_player:
        behavior_rule = """
- 이 응답은 대화가 아니라 기억 복기다.
- 반드시 1인칭 독백처럼 답한다.
- 자신의 이름을 직접 부르지 않는다.
- 기억이 흐릿하면 확신하지 않는 표현을 쓴다.
- 그래도 사건 해결에 도움이 되는 실마리 하나는 남긴다.
""".strip()
    else:
        mode = response_policy.get("mode", "normal")
        reason = response_policy.get("reason", "")
        mode_rule_map = {
            "avoid": f"- 질문이 '{reason}'에 닿았으므로 답을 흐리거나 회피한다.",
            "deny": f"- 질문이 '{reason}'에 닿았으므로 그 사실을 부인한다.",
            "minimize": f"- 질문이 '{reason}'에 닿았으므로 자신의 책임을 축소한다.",
            "shift_blame": f"- 질문이 '{reason}'에 닿았으므로 다른 사람이나 상황 탓으로 돌린다.",
            "normal": "- 직접 본 것 중심으로만 짧게 답한다.",
        }
        behavior_rule = mode_rule_map.get(mode, "- 직접 본 것 중심으로만 짧게 답한다.")

    return f"""
너는 '{character.get('name')}'이다.
절대 AI라고 말하지 말고 캐릭터 시점으로만 답해라.

[사용자 질문]
{user_input}

[관련 직접 기억]
{visible_text}

[관련 추론]
{inferred_text}

[말하면 안 되는 영역]
{blocked}

[캐릭터 핵심]
- 공개 프로필: {character.get('public_profile', '')}
- 핵심 개념: {character.get('core_concept', '')}
- 표면 성격: {personality.get('surface', character.get('personality', ''))}
- 내면 성격: {personality.get('inner', '') if isinstance(personality, dict) else ''}
- 압박 시 변화: {personality.get('under_pressure', '') if isinstance(personality, dict) else ''}
- 기본 말투: {speech_style.get('baseline', character.get('speech_style', '')) if isinstance(speech_style, dict) else character.get('speech_style', '')}
- 목표: {character.get('goal', '')}
- 일관성 규칙: {character.get('consistency_rules', [])}

[행동 지침]
{behavior_rule}
- 설정에 없는 사실은 만들지 않는다.
- 직접 본 것과 추론한 것을 섞어 말하더라도, 추론은 확정적으로 말하지 않는다.
- 답변은 2~5문장으로 짧게 한다.
""".strip()


def generate_character_reply(character, user_input):
    client = get_openai_client()
    if client is None:
        return "OPENAI_KEY가 설정되지 않아 임시 응답으로 표시됩니다. secrets에 키를 넣어주세요."

    try:
        query = normalize_question(user_input)
        memories = retrieve_relevant_memory(character, query)
        bounded_knowledge = apply_knowledge_boundary(character, memories, query)
        response_policy = apply_lie_strategy(character, bounded_knowledge, query)
        prompt = build_reply_prompt(character, user_input, response_policy)

        response = client.responses.create(
            model=st.session_state["selected_model"],
            input=[
                {"role": "system", "content": "너는 추리 게임 캐릭터를 일관되게 연기한다."},
                {"role": "user", "content": prompt},
            ],
        )

        reply = (response.output_text or "").strip()
        if not reply:
            return "...지금은 바로 떠오르지 않는다."
        return reply

    except Exception as e:
        return f"API 응답 생성 중 오류가 발생했습니다: {e}"


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



def render_character_image(character, height=220, placeholder_text="초상화 자리"):
    if character and character.get("image") and Path(character["image"]).exists():
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
                st.caption("모든 심문 기회를 사용했습니다. 이제 범인을 지목하세요.")
            else:
                st.caption("인물을 선택하면 심문이 시작됩니다.")
        else:
            st.caption("게임 시작 후 광장에서 심문할 수 있습니다.")

        st.markdown(
            f"**심문 횟수:** {st.session_state['total_interrogations_used']} / {st.session_state['max_total_interrogations']}"
        )
        for character in CHARACTERS:
            st.markdown("---")
            render_character_image(character, height=140, placeholder_text="초상화 자리")

            button_disabled = (not interrogation_enabled) or interrogation_active or no_more_turns or st.session_state["game_over"]

            if st.button(
                character["name"],
                key=f"select_{character['id']}",
                use_container_width=True,
                disabled=button_disabled,
            ):
                if start_interrogation(character["id"]):
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
    opening_slides = [
        {
            "title": "오프닝 1",
            "body": "12년 전, 한 아이가 흔적도 없이 사라졌다. 사건은 실종으로 마무리되었지만, 진실은 아직 묻혀 있다.",
            "placeholder": "오프닝 이미지 1 자리",
        },
        {
            "title": "오프닝 2",
            "body": "사건 당시 가족, 이웃, 그리고 수사 담당 형사까지. 모두가 무언가를 보았지만, 각자의 방식으로 기억을 감추고 있다.",
            "placeholder": "오프닝 이미지 2 자리",
        },
        {
            "title": "오프닝 3",
            "body": "시간이 흐르며 진술은 흐려졌고, 거짓말은 기억처럼 굳어졌다. 하지만 모순은 완전히 사라지지 않았다.",
            "placeholder": "오프닝 이미지 3 자리",
        },
        {
            "title": "오프닝 4",
            "body": "당신은 제한된 심문 기회 안에 사람들의 말과 기억의 틈을 파고들어야 한다. 누가 진실을 숨기고 있는가.",
            "placeholder": "오프닝 이미지 4 자리",
        },
        {
            "title": "오프닝 5",
            "body": "이제 광장으로 나가 진실을 마주할 시간이다. 다섯 인물을 만나고, 숨겨진 사건의 실체를 밝혀라.",
            "placeholder": "오프닝 이미지 5 자리",
        },
    ]

    slide_index = st.session_state["opening_slide_index"]
    slide = opening_slides[slide_index]

    st.markdown("## 사건 오프닝")
    st.caption(f"{slide_index + 1} / {len(opening_slides)}")
    st.markdown(f"### {slide['title']}")
    render_image_placeholder(slide["placeholder"], height=280)
    st.write(slide["body"])

    prev_col, center_col, next_col = st.columns([1, 2, 1])
    with prev_col:
        if st.button("← 이전", use_container_width=True, disabled=slide_index == 0):
            st.session_state["opening_slide_index"] -= 1
            st.rerun()
    with next_col:
        if st.button("다음 →", use_container_width=True, disabled=slide_index == len(opening_slides) - 1):
            st.session_state["opening_slide_index"] += 1
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    _, center_button_col, _ = st.columns([1, 1, 1])
    with center_button_col:
        if st.button(
            "광장으로 이동",
            use_container_width=True,
            disabled=slide_index != len(opening_slides) - 1,
        ):
            st.session_state["page"] = "main"
            st.rerun()


# =====================================================
# 광장
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
        remaining = st.session_state["max_total_interrogations"] - st.session_state["total_interrogations_used"]
        st.info(f"왼쪽 사이드바에서 심문할 등장인물을 선택하세요. 남은 심문 횟수: {remaining}회")

        _, _, button_col = st.columns([5, 2, 1])
        with button_col:
            if st.button("범인 지목", use_container_width=True, disabled=st.session_state["game_over"]):
                open_accusation_page()
                st.rerun()
        return

    character = get_character_by_id(selected_character_id)
    if character is None:
        st.error("선택한 등장인물 정보를 찾을 수 없습니다.")
        return

    section_title = "기억 되짚기" if "플레이어" in character["name"] else "심문"
    st.markdown(f"## {character['name']} {section_title}")

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
            st.warning("이번 심문에서는 질문 3개를 모두 사용했습니다. 돌아가기를 눌러 광장으로 이동하세요.")
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
            input_placeholder = (
                f"기억을 더듬어 보기 ({questions_used + 1}/{max_questions})"
                if "플레이어" in character["name"]
                else f"{character['name']}에게 질문하기 ({questions_used + 1}/{max_questions})"
            )
            user_input = st.chat_input(input_placeholder)
            if user_input:
                add_message(selected_character_id, "user", user_input)
                reply = generate_character_reply(character, user_input)
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
    st.write("버튼을 눌러 범인이라고 생각하는 인물을 추가하거나 해제하세요.")

    if st.button("광장으로 돌아가기"):
        st.session_state["page"] = "main"
        st.rerun()

    cols = st.columns(len(CHARACTERS))
    for idx, character in enumerate(CHARACTERS):
        with cols[idx]:
            render_character_image(character, height=170, placeholder_text="초상화 자리")
            selected = character["id"] in st.session_state["accused_characters"]
            label = f"✔ {character['name']}" if selected else character['name']
            if st.button(label, key=f"accuse_select_{character['id']}", use_container_width=True):
                toggle_accused_character(character["id"])
                st.rerun()

    selected_names = [get_character_by_id(char_id)["name"] for char_id in st.session_state["accused_characters"]]
    st.caption(f"선택된 인물: {', '.join(selected_names) if selected_names else '없음'}")

    reason = st.text_area(
        "왜 이 인물들이 범인이라고 생각하나요?",
        value=st.session_state["accusation_reason"],
        height=160,
        placeholder="핵심 근거를 적어보세요. 정답 처리는 핵심 키워드 2개 이상이 필요합니다.",
    )
    st.session_state["accusation_reason"] = reason

    if st.button("판정 받기", use_container_width=True):
        judge_accusation()
        st.rerun()


# =====================================================
# 판정 화면
# =====================================================
def render_result_page():
    selected_characters = [get_character_by_id(char_id) for char_id in st.session_state["accused_characters"]]
    selected_characters = [char for char in selected_characters if char is not None]

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

    if selected_characters:
        image_cols = st.columns(len(selected_characters))
        for idx, character in enumerate(selected_characters):
            with image_cols[idx]:
                render_character_image(character, height=240, placeholder_text="지목한 인물의 초상화 자리")
                st.markdown(f"### {character['name']}")

    st.markdown("### 제출한 지목 이유")
    st.info(st.session_state["accusation_reason"] or "입력된 이유 없음")

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
            if st.button("광장으로 돌아가기", use_container_width=True):
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
