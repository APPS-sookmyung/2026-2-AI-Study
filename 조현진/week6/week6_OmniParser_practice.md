개요
6주차 조현진 OmniParser 실습

논문: OmniParser for Pure Vision Based GUI Agent (Microsoft Research, 2024.08)
코드: https://github.com/microsoft/OmniParser
가중치: https://huggingface.co/microsoft/OmniParser-v2.0
요약:
GUI 화면용으로 만든 OmniParser 공개 코드를 Colab에서 실행하고 IKEA 조립 설명서 그림에 적용. 4주차 리뷰에서 추측으로 남긴 한계를 직접 확인하는 실습

추가한 파일
README.md : 실습 내용 정리
omniparser_ikea.ipynb : 실습 노트북 (Colab T4 GPU 기준)
results/ : 결과 그림과 요소 목록 csv (실행 후 추가 예정)

내용 정리

1. 실습 목적
4주차 리뷰의 이후 생각해 볼 부분에 남긴 의문 세 가지를 직접 확인
실험이 전부 UI 화면인데 선화 다이어그램이나 조립 설명서에서도 탐지가 되는지
공개된 코드가 논문과 무엇이 달라졌는지
반복 요소 실패 사례가 길이만 다른 나사에서 그대로 재현되는지

졸업 연구(조립 과정 VLM 분석)와 직접 연결. 설명서 그림에서 부품을 찾아 번호를 붙일 수 있는지는 연구에서도 그대로 필요한 기능
-> 잘 되면 연구에 쓸 도구가 생기고, 안 되면 어디서 왜 안 되는지가 문제 제기 자료가 됨

2. 확인할 질문
번호	질문	예상	근거
Q1	설명서 부품에 박스가 쳐지는가	큰 판재는 잡히고 작은 나사는 많이 놓침	탐지 모델이 기본 설정에서 640 크기로 줄여서 봄
Q2	붙은 설명이 쓸모 있는가	GUI 버튼 이름 같은 엉뚱한 설명	설명 모델이 아이콘과 기능 쌍으로만 학습됨
Q3	같은 모양 나사끼리 구별되는가	설명이 같아서 구별 불가	설명 모델 입력이 64x64로 줄어 길이 차이가 사라짐
Q4	크게 보게 하면 나아지는가	Q1만 나아지고 Q2, Q3은 그대로	탐지와 설명이 별개 모델

3. 코드 구조
핵심은 util/utils.py의 get_som_labeled_img 하나. 처리 순서는 아래와 같음

탐지 모델로 상호작용 가능 영역 박스 생성 (predict_yolo)
OCR 결과 박스와 합침
겹치는 박스 제거 (remove_overlap_new). 겹치면 작은 박스를 남김
글자가 아이콘 박스 안에 80% 넘게 들어가 있으면 그 글자를 아이콘 설명으로 사용
글자가 없는 아이콘은 잘라내 64x64로 줄인 뒤 설명 모델에 입력 (get_parsed_content_icon)
번호가 그려진 이미지와 요소 목록 반환

요소 하나의 형식
키	뜻
type	text 또는 icon
bbox	박스 좌표, 0~1 비율, x1 y1 x2 y2
interactivity	누를 수 있는 요소인지
content	글자 내용 또는 설명 모델이 만든 설명
source	정보 출처 (box_ocr_content_ocr / box_yolo_content_ocr / box_yolo_content_yolo)

4. 논문과 코드가 다른 점
항목	논문 (2024.08)	코드 (2026.07 커밋 기준)
탐지 모델	YOLOv8	YOLOv9-E (icon_detect_v3)
설명 모델	BLIP-2	Florence-2 (BLIP-2는 주석 처리된 선택지로 남음)
요소 정보	번호와 설명	누를 수 있는지 여부(interactivity) 추가

4주차에 v2가 Florence2로 바뀌었다고 적었는데 그 사이 탐지 모델도 YOLOv9-E로 교체됨
이번 실습 결과는 논문 버전이 아니라 현재 공개 버전 기준

5. 코드를 읽다 발견한 것
아래는 코드만 보고 한 판단이라 실행으로 확인 필요

탐지 크기 인자가 기본 설정에서 무시됨: get_som_labeled_img에 imgsz를 넘겨도 scale_img=False면 predict_yolo가 imgsz를 모델에 전달하지 않음 -> 항상 640으로 탐지. Gradio 데모의 Icon Detect Image Size 슬라이더도 같은 이유로 효과 없을 것으로 보임
설명 모델 입력이 64x64: 잘라낸 아이콘을 cv2.resize로 64x64 정사각형에 맞춤 -> 길쭉한 나사도 눌려서 길이 정보가 사라짐. Q3의 근거
OCR이 영어 전용: 설명서에서는 부품 번호와 4x 같은 수량 표시만 잡힐 것
글자가 없는 이미지에서 에러: OCR 결과가 비면 ocr_bbox가 None이 되고 다음 줄에서 zip에 그대로 들어감 -> 노트북에서 빈 글자 박스를 하나 넣어 우회

6. 실습 환경과 설치에서 고친 것
환경: Google Colab, T4 GPU, Python 3.13

레포 README대로 하면 지금은 바로 안 돌아감. 고친 것 세 가지

huggingface-cli 명령이 없어짐 -> hf download로 교체
PaddleOCR 옛 버전이 Python 3.13에 설치되지 않음. 3.x는 설치되나 utils.py가 옛 인자(show_log, use_gpu)로 생성해서 에러 -> utils.py에서 PaddleOCR import와 생성 부분을 제거하고 EasyOCR만 사용. 설명서는 글자가 거의 없어 결과 영향 작음
requirements.txt에 윈도우 전용, 에이전트용 패키지가 섞여 있음 -> 파싱에 필요한 것만 설치. Florence-2 원격 코드 호환을 위해 transformers 4.49.0 고정

7. 실습 방법
대조군: 레포의 GUI 예시 스크린샷(imgs/word.png)으로 정상 동작 확인. 여기서 되는데 설명서에서 안 되면 데이터 차이로 판단 가능
실험군: 조립 설명서 2장 (A 부품 목록 페이지, B 조립 단계 페이지). 결과를 보기 전에 사람이 부품 수를 먼저 셈

실험	설정	보려는 것
1 기본	box_threshold 0.05, 640	Q1, Q2
2 크게 보기	scale_img=True, imgsz=1280	Q4
2 확인	scale_img=False, imgsz=1280	5번 발견 확인 -> 기본과 같으면 imgsz 무시
3 같은 나사 비교	잘라낸 그림과 64x64 그림을 나란히 출력	Q3

8. 결과
실행 후 추가 예정

항목	A 부품 목록	B 조립 단계
사람이 센 부품 수
기본에서 잡힌 수
기본에서 놓친 수
부품이 아닌데 잡힌 것
크게 보기에서 잡힌 수		-

확인한 것	결과
GUI 화면에서 정상 동작
imgsz 무시 여부
같은 나사의 설명이 같은지
64x64에서 사람 눈으로 구별되는지
설명이 GUI 용어로 나온 예

이후 생각해 볼 부분

설명서 그림은 IKEA 저작물이라 결과 그림은 일부만 올리고 출처 표기 필요
Q3이 64x64 입력 때문이라면 설명 모델을 바꿔도 해결되지 않음. 입력 크기나 종횡비를 유지하는 쪽을 먼저 시도해 볼 필요
탐지가 되는데 설명만 틀리는 경우라면 박스는 OmniParser로, 설명은 다른 VLM으로 나누는 조합 가능

이후 스터디 주제
번호 유무 비교: 같은 설명서 그림을 원본과 번호 붙인 버전으로 VLM에 넣고 이 단계에서 쓰는 부품이 무엇인지 물어 정답률 비교 -> SoM의 핵심 주장을 설명서에서 재현
원인 분리: 탐지가 놓친 부품에 손으로 박스를 주고 번호만 붙였을 때 VLM이 나아지는지 -> 문제가 탐지인지 설명인지 구분
