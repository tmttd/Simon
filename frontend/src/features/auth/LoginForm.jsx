import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { useAuth } from "../../context/AuthContext";
import styles from "./LoginForm.module.css";

// 스키마(검증) - 규칙은 PLACEHOLDER로 남겨둡니다.
const loginSchema = z.object({
  email: z.string().email("유효한 이메일을 입력하세요."),
  password: z.string().min(8, "8자 이상 입력하세요."),
});

export default function LoginForm() {
  const { login, isAuthenticated, isLoading } = useAuth();
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
      const payload = { email: values.email, password: values.password };
      await login(payload);
      // 로그인 성공 시 AuthProvider가 상태를 변경하고
      // ProtectedRoute가 알아서 페이지를 이동시켜줍니다.
      // 따라서 여기서 navigate를 명시적으로 호출할 필요가 없습니다.
      // navigate(fromPath, { replace: true });
    } catch (err) {
      setErrorMsg(
        err?.response?.data?.detail || "로그인에 실패했습니다."
      );
    }
  };

  // 인증 확인 중이거나 이미 로그인 되었다면 채팅 페이지로 이동
  if (isLoading) {
    return <div style={{ padding: 16 }}>인증 상태 확인 중...</div>;
  }
  if (isAuthenticated) {
    return <Navigate to={fromPath} replace />;
  }


  return (
    <div className={styles.page}>
      <form noValidate onSubmit={handleSubmit(onSubmit)} className={styles.card}>
        <img
          src="/simon_logo_48.png"
          srcSet="/simon_logo_48.png 1x, /simon_logo_96.png 2x, /simon_logo_144.png 3x"
          alt="Simon logo"
          className={styles.logo}
        />
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