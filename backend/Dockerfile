# insuLin_Guide/Dockerfile.backend

# 1. 베이스 이미지 설정
FROM python:3.11-slim

# 2. 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. 작업 디렉토리 설정 및 의존성 설치
WORKDIR /app
COPY ./requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 4. 프로젝트 파일 복사
COPY . /app/

# 5. Gunicorn 실행 (개발 서버가 아닌 실제 서비스용 서버)
# 포트 8000번을 외부에 노출
EXPOSE 8000
ENTRYPOINT [ "./entrypoint.sh" ]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]