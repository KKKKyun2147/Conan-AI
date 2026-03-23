import streamlit as st

# 1. 페이지 설정 (웹 브라우저 탭에 표시될 이름과 아이콘)
st.set_page_config(page_title="AI 탐정 사무소", page_icon="🕵️")

# 2. 제목 및 설명
st.title("🕵️ AI 탐정: 사라진 황금 사과")
st.info("용의자 AI와 대화하며 증거를 수집하세요. 범행을 자백받으면 승리합니다!")

# 3. 레이아웃 나누기 (왼쪽: 정보창, 오른쪽: 채팅창)
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📌 사건 정보")
    st.image("https://via.placeholder.com/200", caption="사건 현장 (예시)") # 실제 이미지 URL로 교체 가능
    
    st.write("**남은 수사 기회:**")
    st.progress(70) # 수사 진행률이나 체력 등을 표시
    
    if st.button("🔍 증거 인벤토리 확인"):
        st.write("- 찢어진 손수건")
        st.write("- 수상한 발자국 사진")

with col2:
    st.subheader("💬 용의자와의 대화")
    # 대화창 구현 (이전 코드의 채팅 로직이 여기 들어갑니다)
    with st.chat_message("assistant"):
        st.write("나... 난 정말 모르는 일이라니까요? 왜 자꾸 나만 의심하는 거죠?")
    
    user_input = st.chat_input("질문을 입력하세요...")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        # 여기에 OpenAI API 호출 로직을 넣으면 완성!

# 4. 마무리 효과
if st.sidebar.button("🎉 사건 해결 선언"):
    st.balloons()
    st.success("축하합니다! 범인을 검거했습니다.")
