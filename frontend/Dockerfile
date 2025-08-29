# Simon/Dockerfile.frontend

# --- 1단계: 빌드 환경 ---
    FROM node:18-alpine AS builder

    WORKDIR /app
    # package.json과 lock 파일을 먼저 복사하여 의존성을 캐싱합니다.
    COPY ./package*.json /app/
    RUN npm install
    # 전체 소스 코드를 복사합니다.
    COPY . /app/
    # 프로덕션용으로 빌드합니다.
    RUN npm run build
    
    # --- 2단계: 프로덕션 환경 ---
    FROM nginx:stable-alpine
    # 빌드 단계에서 생성된 정적 파일들을 Nginx의 기본 웹 루트로 복사합니다.
    COPY --from=builder /app/dist /usr/share/nginx/html

    COPY nginx.conf /etc/nginx/conf.d/default.conf 
    # Nginx가 80번 포트를 사용하도록 노출합니다.
    EXPOSE 80
    # 컨테이너가 시작될 때 Nginx를 실행합니다.
    CMD ["nginx", "-g", "daemon off;"]