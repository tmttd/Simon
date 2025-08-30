import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useLocation } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { api, login } from "../../api/apiClient.js"
import { setAccessToken } from "../../api/tokenStorage.js";
import styles from "./LoginForm.module.css";

// 스키마(검증) - 규칙은 PLACEHOLDER로 남겨둡니다.
const loginSchema = z.object({
  email: z.string().email("유효한 이메일을 입력하세요."),
  password: z.string().min(8, "8자 이상 입력하세요."),
});

export default function LoginForm() {
    const navigate = useNavigate();
    const location = useLocation();
    const fromPath = location.state?.from?.pathname || "/chat";

    const [errorMsg, setErrorMsg] = useState("");
  
    const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "", // 필요시 기본값 조정 가능
      password: "",
    },
    mode: "onTouched",
  });

  const onSubmit = async (values) => {
    setErrorMsg("");
    try {
        // [L2] 요청 페이로드 매핑 (백엔드가 기대하는 키 이름으로)
        const payload = { email: values.email, password: values.password };
  
        // [L3] 로그인 요청 (리프레시 쿠키는 서버가 Set-Cookie로 내려줌)
        const res = await login(payload);
  
        // [L4] access 추출 (응답 JSON 형태에 맞춰)
        const access = res.access;
  
        if (!access) throw new Error("access 토큰을 받지 못했습니다.");
        
        // [L5] access 저장 (메모리/세션 등 tokenStorage 정책에 맞게)
        setAccessToken(access);
  
        // [L6] 기본 Authorization 헤더 동기화 (이후 보호 API 호출 대비)
        api.defaults.headers.common.Authorization = `Bearer ${access}`;
  
        navigate(fromPath, { replace: true });

      } catch (err) {
        // [L7] 사용자에게 보여줄 에러 메시지 (서버 메시지 우선)
        setErrorMsg(
          err?.response?.data?.detail || "로그인에 실패했습니다."
        );
      }
    };

    return (
      <div className={styles.page}>
        <form noValidate onSubmit={handleSubmit(onSubmit)} className={styles.card}>
          <h1 className={styles.title}>Simon-AI 로그인</h1>
          <p className={styles.subtitle}>계정에 접속하여 계속 진행하세요.</p>
  
          {errorMsg && (
            <div role="alert" className={styles.alert}>{errorMsg}</div>
          )}
  
          <label htmlFor="email" className={styles.label}>이메일</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            {...register("email")}
            aria-invalid={!!errors.email}
            aria-describedby="email-error"
            className={`${styles.input} ${errors.email ? styles.isInvalid : ""}`}
          />
          {errors.email && (
            <div id="email-error" className={styles.errorText}>
              {errors.email.message?.toString()}
            </div>
          )}
  
          <label htmlFor="password" className={styles.label}>비밀번호</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="********"
            {...register("password")}
            aria-invalid={!!errors.password}
            aria-describedby="password-error"
            className={`${styles.input} ${errors.password ? styles.isInvalid : ""}`}
          />
          {errors.password && (
            <div id="password-error" className={styles.errorText}>
              {errors.password.message?.toString()}
            </div>
          )}
  
          <button
            type="submit"
            disabled={isSubmitting}
            className={styles.submitBtn}
          >
            {isSubmitting ? "로그인 중입니다..." : "로그인"}
          </button>
        </form>
      </div>
    );
  }