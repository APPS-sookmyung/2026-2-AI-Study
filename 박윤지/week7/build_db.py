import re
import shutil
from pathlib import Path

import fitz
import pdfplumber
import pandas as pd
from tqdm import tqdm

from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


PDF_DIR = Path("pdfs")
DB_DIR = "./chroma_db"
COLLECTION_NAME = "rag_documents"
EMBEDDING_MODEL = "jhgan/ko-sroberta-nli"


def clean_text(text):
    if text is None:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_page_text(pdf_path):
    """PyMuPDF로 PDF의 페이지별 텍스트를 추출한다."""
    docs = []

    with fitz.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf):
            blocks = page.get_text("blocks")
            # 위→아래, 왼쪽→오른쪽 순서로 정렬
            blocks = sorted(blocks, key=lambda block: (block[1], block[0]))

            texts = []
            for block in blocks:
                text = clean_text(block[4])
                if text:
                    texts.append(text)

            page_text = "\n".join(texts)
            if page_text:
                docs.append(
                    Document(
                        page_content=page_text,
                        metadata={
                            "source": pdf_path.name,
                            "page": page_num + 1,
                            "type": "text",
                        },
                    )
                )

    return docs


def extract_tables(pdf_path):
    """pdfplumber로 PDF 안의 표를 추출해 Markdown 문서로 저장한다."""
    docs = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables() or []

            for table_id, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue

                rows = [
                    [clean_text(cell) if cell else "" for cell in row]
                    for row in table
                ]

                df = pd.DataFrame(rows)
                df.columns = df.iloc[0]
                df = df.iloc[1:].reset_index(drop=True)
                df.columns = [
                    f"col{i}" if str(col).strip() == "" else str(col)
                    for i, col in enumerate(df.columns)
                ]

                markdown = df.to_markdown(index=False)
                if markdown.strip():
                    docs.append(
                        Document(
                            page_content=markdown,
                            metadata={
                                "source": pdf_path.name,
                                "page": page_num + 1,
                                "table": table_id + 1,
                                "type": "table",
                            },
                        )
                    )

    return docs


def main():
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"{PDF_DIR} 폴더에 PDF 파일이 없습니다. PDF를 넣고 다시 실행하세요."
        )

    all_documents = []

    for pdf_path in tqdm(pdf_files, desc="PDF 처리", unit="file"):
        text_docs = extract_page_text(pdf_path)
        table_docs = extract_tables(pdf_path)
        all_documents.extend(text_docs)
        all_documents.extend(table_docs)

        print(
            f"\n{pdf_path.name}\n"
            f"텍스트 페이지: {len(text_docs)}개 / 표: {len(table_docs)}개"
        )

    if not all_documents:
        raise ValueError("PDF에서 텍스트나 표를 추출하지 못했습니다.")

    print(f"\n총 추출 Document 수: {len(all_documents)}")

    # 노트북의 8-3에서 사용하는 임베딩 모델과 동일하게 맞춘다.
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # 노트북의 SemanticChunker 방식 유지
    splitter = SemanticChunker(embeddings)
    split_docs = splitter.split_documents(all_documents)

    print(f"청킹 완료: {len(split_docs)}개")

    # 재실행 시 기존 DB에 같은 문서가 중복 추가되지 않도록 초기화
    db_path = Path(DB_DIR)
    if db_path.exists():
        shutil.rmtree(db_path)

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=DB_DIR,
        embedding_function=embeddings,
    )

    batch_size = 50
    for start in tqdm(range(0, len(split_docs), batch_size), desc="Chroma 저장"):
        vectorstore.add_documents(split_docs[start : start + batch_size])

    print(f"\n저장 완료: {vectorstore._collection.count()}개 벡터")
    print(f"저장 위치: {db_path.resolve()}")


if __name__ == "__main__":
    main()
