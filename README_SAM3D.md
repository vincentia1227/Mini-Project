# 가구 이미지 → 3D 모델 (SAM 3D)

`Input_Picture` 폴더의 흰색 배경 가구 이미지를 [fal.ai SAM 3D](https://fal.ai/models/fal-ai/sam-3/3d-objects/api) API로 3D(.ply, .glb)로 변환하고,  
`Output_Modeling` 아래에 **이미지별 폴더**로 저장합니다.

## 사용 방법

1. **API 키 설정** (둘 중 하나)
   - 환경 변수: `FAL_KEY=your_key` 설정 후 실행
   - 또는 프로젝트 폴더에 `.env` 파일 생성 후 `FAL_KEY=your_key` 입력  
     (`.env.example`을 복사해 `.env`로 이름 변경 후 키 입력)

2. **실행**
   ```bash
   cd "D:\01. Architecture\03. Architon\D-day Architon"
   npm run run
   ```
   또는
   ```bash
   node run-sam3d.mjs
   ```

## 폴더 구조

- **입력:** `Input_Picture/` — 변환할 이미지 (.png, .jpg, .jpeg, .webp)
- **출력:** `Output_Modeling/<이미지이름>/`
  - `이미지이름.ply` — Gaussian splat (메인)
  - `이미지이름.glb` — 3D 메시 (있을 경우)
  - 객체가 여러 개면 `이미지이름_object_0.ply`, `이미지이름_object_0.glb` 등
  - `이미지이름_artifacts.zip` — 전체 결과 번들 (있을 경우)

## 요구 사항

- Node.js 18+
- [fal.ai](https://fal.ai) 계정 및 API 키
