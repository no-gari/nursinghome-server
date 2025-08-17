import os
import chromadb
from sentence_transformers import SentenceTransformer
from django.conf import settings
from core.models import Facility, FacilityBasic, FacilityEvaluation, FacilityStaff, FacilityProgram, FacilityLocation, FacilityNonCovered
from typing import List, Dict, Any
import openai

class RAGService:
    def __init__(self):
        # ChromaDB 클라이언트 초기화
        self.chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_DB_PATH))
        self.collection_name = "nursinghome_facilities"

        # 임베딩 모델 초기화
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

        # OpenAI 클라이언트 초기화
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY

        # 컬렉션 초기화
        self._init_collection()

    def _init_collection(self):
        """ChromaDB 컬렉션 초기화"""
        try:
            # 기존 컬렉션이 있으면 가져오기
            self.collection = self.chroma_client.get_collection(self.collection_name)
        except:
            # 없으면 새로 생성
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "요양원 시설 정보"}
            )

    def embed_facilities(self):
        """모든 요양원 데이터를 벡터화하여 ChromaDB에 저장"""
        facilities = Facility.objects.all()

        documents = []
        metadatas = []
        ids = []

        for facility in facilities:
            # 시설 기본 정보 문서 생성
            doc_parts = [
                f"시설명: {facility.name}",
                f"종류: {facility.kind}",
                f"등급: {facility.grade}",
                f"이용가능: {facility.availability}",
            ]

            if facility.capacity:
                doc_parts.append(f"정원: {facility.capacity}명")
            if facility.occupancy:
                doc_parts.append(f"현원: {facility.occupancy}명")
            if facility.waiting:
                doc_parts.append(f"대기: {facility.waiting}명")

            # 기본정보 추가
            basic_items = facility.basic_items.all()
            if basic_items:
                doc_parts.append("기본정보:")
                for item in basic_items:
                    doc_parts.append(f"- {item.title}: {item.content}")

            # 평가정보 추가
            eval_items = facility.evaluation_items.all()
            if eval_items:
                doc_parts.append("평가정보:")
                for item in eval_items:
                    doc_parts.append(f"- {item.title}: {item.content}")

            # 인력현황 추가
            staff_items = facility.staff_items.all()
            if staff_items:
                doc_parts.append("인력현황:")
                for item in staff_items:
                    doc_parts.append(f"- {item.title}: {item.content}")

            # 프로그램 운영 추가
            program_items = facility.program_items.all()
            if program_items:
                doc_parts.append("프로그램 운영:")
                for item in program_items:
                    doc_parts.append(f"- {item.title}: {item.content}")

            # 위치 정보 추가
            location_items = facility.location_items.all()
            if location_items:
                doc_parts.append("위치정보:")
                for item in location_items:
                    doc_parts.append(f"- {item.title}: {item.content}")

            # 비급여 항목 추가
            noncov_items = facility.noncovered_items.all()
            if noncov_items:
                doc_parts.append("비급여 항목:")
                for item in noncov_items:
                    doc_parts.append(f"- {item.title}: {item.content}")

            document = "\n".join(doc_parts)

            documents.append(document)
            metadatas.append({
                "facility_id": facility.id,
                "facility_code": facility.code,
                "facility_name": facility.name,
                "facility_kind": facility.kind,
                "facility_grade": facility.grade,
                "facility_availability": facility.availability,
            })
            ids.append(f"facility_{facility.id}")

        # 기존 데이터 삭제 후 새로 추가
        try:
            self.collection.delete()
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "요양원 시설 정보"}
            )
        except:
            pass

        # 배치 단위로 추가 (ChromaDB 제한 때문에)
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]

            # 임베딩 생성
            embeddings = self.embedding_model.encode(batch_docs).tolist()

            self.collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids,
                embeddings=embeddings
            )

        return len(documents)

    def search_facilities(self, query: str, n_results: int = 5) -> List[Dict]:
        """사용자 질문에 관련된 요양원들을 검색"""
        # 쿼리 임베딩
        query_embedding = self.embedding_model.encode([query]).tolist()

        # 유사한 문서 검색
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            include=['documents', 'metadatas', 'distances']
        )

        return results

    def generate_answer(self, query: str, context_docs: List[str]) -> str:
        """검색된 문서들을 바탕으로 답변 생성"""
        if not settings.OPENAI_API_KEY:
            return "OpenAI API 키가 설정되지 않았습니다. 검색 결과만 제공합니다."

        # 컨텍스트 준비
        context = "\n\n".join([f"[시설 {i+1}]\n{doc}" for i, doc in enumerate(context_docs)])

        # 프롬프트 구성
        prompt = f"""
다음은 한국의 요양원 시설 정보입니다. 사용자의 질문에 대해 이 정보를 바탕으로 정확하고 도움이 되는 답변을 제공해주세요.

<요양원 정보>
{context}

<사용자 질문>
{query}

<답변 가이드라인>
1. 제공된 정보만을 바탕으로 답변하세요
2. 구체적인 시설명, 등급, 위치 등을 포함하여 답변하세요
3. 사용자가 요양원 선택에 도움이 되도록 비교 정보를 제공하세요
4. 정보가 부족한 경우 솔직히 말씀드리세요
5. 친근하고 전문적인 톤으로 답변하세요

답변:
"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "당신은 요양원 정보 전문가입니다. 사용자가 적절한 요양원을 찾을 수 있도록 정확하고 유용한 정보를 제공합니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"답변 생성 중 오류가 발생했습니다: {str(e)}"

    def chat(self, query: str) -> Dict[str, Any]:
        """전체 RAG 프로세스 실행"""
        # 1. 관련 문서 검색
        search_results = self.search_facilities(query)

        # 2. 검색 결과가 있는지 확인
        if not search_results['documents'][0]:
            return {
                "answer": "죄송합니다. 질문과 관련된 요양원 정보를 찾을 수 없습니다.",
                "sources": [],
                "query": query
            }

        # 3. 컨텍스트 문서 준비
        context_docs = search_results['documents'][0]
        metadatas = search_results['metadatas'][0]

        # 4. LLM으로 답변 생성
        answer = self.generate_answer(query, context_docs)

        # 5. 결과 반환
        return {
            "answer": answer,
            "sources": [
                {
                    "facility_name": meta['facility_name'],
                    "facility_grade": meta['facility_grade'],
                    "facility_id": meta['facility_id']
                } for meta in metadatas
            ],
            "query": query
        }
