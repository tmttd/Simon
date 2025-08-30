// frontend/lib/apiClient.js
import axios from "axios";
import { getAccessToken, setAccessToken, clearAccessToken } from "./tokenStorage";

const BASE_URL = "/api";

let refreshPromise = null; // 싱글-플라이트 보관

export const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: false,
});

const isAuthRoute = (url = "") => {
  const AuthRoute = ["auth/token/", "auth/token/refresh/"];
  return AuthRoute.some((p) => url.includes(p));
};

function getRefreshOnce() {
  if (!refreshPromise) {
    refreshPromise = api.post("auth/token/refresh/", null, { withCredentials: true })
      .then((res) => res.data)        // 성공 시 res.data 반환
      .finally(() => {
        refreshPromise = null;        // 성공/실패 상관없이 항상 실행
      });
  }
  return refreshPromise;              // 진행 중이면 그 Promise 재사용
}

// 요청 인터셉터: Access 있으면 Authorization 주입(인증 엔드포인트는 제외)
api.interceptors.request.use((config) => {
  if (!isAuthRoute(config.url)) {
    const access = getAccessToken();
    if (access) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${access}`;
    }
  }
  return config;
});

// interceptors.response는 onFulfilled와 onRejected 두 개의 객체를 반환함. use는 두 개를 각각
// 사용하는 콜백함수를 지정해주겠다는 뜻.
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const { config, response } = error || {}; // config는 요청의 상태, response는 서버로부터의 응답
    if (!response || response.status !== 401 || isAuthRoute(config?.url)) {
      return Promise.reject(error);
    } 
    
    if (config._retry) {
      clearAccessToken();
      return Promise.reject(error);
    }
    config._retry = true;

    let refreshData;
    try {
      refreshData = await getRefreshOnce();
    } catch (e) {
      // (선택) 서버 쿠키 정리: HttpOnly refresh 삭제 시도
      try {
      await api.post("auth/logout/", null, { withCredentials: true });
      } catch (_) {
      // 서버 측 정리가 실패해도 로컬 정리는 계속
      }
      clearAccessToken()
      return Promise.reject(e)
    }

    const access = refreshData["access"];

    setAccessToken(access);
    api.defaults.headers.common.Authorization = `Bearer ${access}`;

    /* 원래 요청을 1회 재시도 */
    const nextHeaders = { ...(config.headers || {}), Authorization: `Bearer ${access}` };
    // 디버그 표식: 재시도 요청에만 붙이는 헤더(네트워크 탭에서 확인용)
    nextHeaders["X-Debug-Retry"] = "1";
    // config를 얕게 복제해 전달(머지/참조 이슈 방지)
    return api.request({ ...config, headers: nextHeaders });  }
);

// 3) login 헬퍼에서 access 적용만 보장(쿠키는 서버가 심음)
export async function login({ email, password }) {
  const res = await api.post("auth/token/", { email, password });
  return res.data;
}

export async function me() {
  const res = await api.get("auth/me/");
  return res.data;
}

export async function logout() {
  clearAccessToken();
  // 서버 revoke는 선택
}