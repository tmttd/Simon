from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

# === 쿠키 설정 상수 (cookie settings)===
COOKIE_NAME = "refresh"
COOKIE_PATH = "/api/auth/"
COOKIE_SAMESITE = "Lax"
COOKIE_SECURE = False
MAX_AGE_SECONDS = 86400 # 1일

def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """ HttpOnly 쿠키를 심는 함수 """
    response.set_cookie(
        key=COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=MAX_AGE_SECONDS,
    )

class CookieTokenObtainPairView(TokenObtainPairView):
    """ 엔드포인트: api/auth/token 
        email: <이메일>, password: <비밀번호>가 body로 요청되면
        access 토큰을 body에 넣어서 보내주고, refresh 토큰(HttpOnly)은 Set-Cookie를 통해 헤더로 보낸다.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True) # 여기서 access토큰과 refresh 토큰이 생성됨.

        access_token = serializer.validated_data.get("access") # 생성된 access토큰을 get하면 끝.
        refresh_token = serializer.validated_data.get("refresh") # 생성된 refresh토큰을 get하면 끝!

        resp = Response({"access": access_token}, status=status.HTTP_200_OK)
        resp["Cache-Control"] = "no-store"
        set_refresh_cookie(resp, refresh_token)
        return resp  

class CookieTokenRefreshView(TokenRefreshView):
    """
    재발급:
    - 요청 바디 없이, 헤더 속 쿠키의 refresh 토큰을 이용하여 access를 재발급.
    - ROTATE_REFRESH_TOKENS = True로 설정된 경우 새 refresh 토큰을 발급하여 쿠키로 재설정.
    - 응답 바디에는 access만 반환.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # 1) 쿠키에서 refresh 추출
        refresh_from_cookie = request.COOKIES.get(COOKIE_NAME)
        if not refresh_from_cookie:
            return Response({'detail': 'Refresh cookie missing'}, status=status.HTTP_401_UNAUTHORIZED)
        # 2) serializer에 쿠키값 주입
        serializer = self.get_serializer(data={'refresh': refresh_from_cookie})
        serializer.is_valid(raise_exception=True) 
        # 이 한 줄로 access 토큰과 refresh 토큰이 발급됨. 
        # ROATION과 BLACKLIST 작업까지 수행됨.

        data = serializer.validated_data
        access_token = data.get("access")
        new_refresh_token = data.get("refresh")
        # 3) 응답 구성(body에는 access만)
        resp = Response({"access": access_token}, status=status.HTTP_200_OK)
        # 4) 회전 시 새로운 refresh를 쿠키로 재설정
        if new_refresh_token:
            set_refresh_cookie(resp, new_refresh_token)
        # 5) 캐시 방지(권장)
        resp["Cache-Control"] = "no-store"
        return resp

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "password": user.password,
            "is_superuser": user.is_superuser,
        })
    
class LogoutView(APIView):
    """
    엔드포인트: api/auth/logout/
    로그아웃
    - 쿠키의 refresh 토큰을 확인하여 이를 blacklist에 저장.
    - 동일 속성(Path/Samesite/Secure)의 refresh 쿠키 삭제.
    - 클라이언트에게 아무것도 반환하지 않음. (HTTP_204 No Content)
    """    
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(COOKIE_NAME)
        try: 
            if refresh_token:
                RefreshToken(refresh_token).blacklist()
                pass
        except Exception:
            pass

        resp = Response(status=status.HTTP_204_NO_CONTENT)
        # 쿠키 삭제(발급과 동일 속성)
        resp.delete_cookie(
            key=COOKIE_NAME,
            path=COOKIE_PATH,
            samesite=COOKIE_SAMESITE,
        )
        # 쿠키 사용 안 함
        resp["Cache-Control"] = "no-store"
        return resp
