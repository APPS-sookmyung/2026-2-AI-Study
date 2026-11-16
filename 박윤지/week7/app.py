import os

import streamlit as st
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


load_dotenv()

DB_DIR = "./chroma_db"
COLLECTION_NAME = "rag_documents"
EMBEDDING_MODEL = "jhgan/ko-sroberta-nli"

st.set_page_config(page_title="RAG 챗봇", page_icon="💬")
st.title("💬 RAG 기반 문서 챗봇")
st.caption("업로드한 PDF 문서를 검색해 근거를 바탕으로 답변합니다.")


@st.cache_resource
def get_retriever():
    """저장된 Chroma DB를 열고 검색기를 반환한다."""
    if not os.path.isdir(DB_DIR):
        raise FileNotFoundError(
            "chroma_db가 없습니다. 먼저 터미널에서 `python build_db.py`를 실행하세요."
        )

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    db = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=DB_DIR,
        embedding_function=embeddings,
    )
    return db.as_retriever(search_kwargs={"k": 3})


@st.cache_resource
def get_llm():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(".env 파일에 GEMINI_API_KEY를 설정하세요.")

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    return ChatGoogleGenerativeAI(
        model=model_name,
        gemini_api_key=api_key,
        temperature=0.2,
    )


def get_response(query):
    # ① 질문과 관련된 문서 청크 검색
    docs = get_retriever().invoke(query)

    if not docs:
        return "관련 문서를 찾지 못했습니다.", []

    # ② 검색한 문서 내용을 하나의 컨텍스트로 구성
    context = "\n\n".join(
        f"[출처: {doc.metadata.get('source', '알 수 없음')}, "
        f"페이지: {doc.metadata.get('page', '알 수 없음')}]\n"
        f"{doc.page_content}"
        for doc in docs
    )

    # ③ 검색 결과를 참고해 Gemini가 답변하도록 프롬프트 구성
    prompt = f"""
        너는 업로드된 문서를 바탕으로 질문에 답하는 문서 안내 챗봇이야.

        아래 [참고 문서]에 있는 내용을 우선적으로 사용해 답변해.
        참고 문서에서 확인할 수 없는 내용은 임의로 만들어내지 말고,
        문서에서 확인할 수 없다고 솔직하게 말해줘.
        답변은 한국어로 이해하기 쉽게 작성해줘.

        [참고 문서]
        {context}

        [질문]
        {query}

        [답변]
    """
    response = get_llm().invoke(prompt)
    content = response.content

    # Gemini 응답에서 실제 텍스트만 추출
    if isinstance(content, list):
        answer = "\n\n".join(
            item["text"]
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        )
    else:
        answer = content

    return answer, docs


# 대화 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "무엇을 도와드릴까요?"}
    ]

# 기존 대화 출력
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 사용자 질문 처리
if query := st.chat_input("문서에 대해 질문하세요"):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("문서를 검색하고 답변을 생성하고 있습니다..."):
            try:
                answer, docs = get_response(query)
                st.markdown(answer)

                # 검색 근거 확인
                if docs:
                    with st.expander("참고한 문서 확인"):
                        for index, doc in enumerate(docs, start=1):
                            source = doc.metadata.get("source", "알 수 없음")
                            page = doc.metadata.get("page", "알 수 없음")
                            st.markdown(f"**{index}. {source} (페이지 {page})**")
                            st.write(doc.page_content)

                st.session_state.messages.append(
                    {"role": "assistant", "content": answer}
                )

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")