import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { signup } from "../../api/apiClient";
import styles from "./SignupForm.module.css";

// 스키마(검증)
const signupSchema = z.object({
  email: z.string().email("유효한 이메일을 입력하세요."),
  username: z.string().min(2, "닉네임은 2자 이상 입력하세요.").max(150, "닉네임은 150자 이하로 입력하세요.").optional().or(z.literal("")),
  password: z.string().min(8, "8자 이상 입력하세요."),
  passwordConfirm: z.string().min(8, "8자 이상 입력하세요."),
  firstName: z.string().min(1, "이름을 입력하세요."),
  lastName: z.string().min(1, "성을 입력하세요."),
}).refine((data) => data.password === data.passwordConfirm, {
  message: "비밀번호가 일치하지 않습니다.",
  path: ["passwordConfirm"],
});

export default function SignupForm() {
  const navigate = useNavigate();
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      email: "",
      username: "",
      password: "",
      passwordConfirm: "",
      firstName: "",
      lastName: "",
    },
    mode: "onTouched",
  });

  const onSubmit = async (values) => {
    setErrorMsg("");
    setSuccessMsg("");
    try {
      await signup(values);
      setSuccessMsg("회원가입이 완료되었습니다! 로그인 페이지로 이동합니다.");
      setTimeout(() => {
        navigate("/login");
      }, 2000);
    } catch (err) {
      const errorDetail = err?.response?.data;
      if (typeof errorDetail === 'object') {
        // 필드별 에러 메시지 처리
        const errorMessages = [];
        for (const [field, messages] of Object.entries(errorDetail)) {
          if (Array.isArray(messages)) {
            errorMessages.push(...messages);
          } else {
            errorMessages.push(messages);
          }
        }
        setErrorMsg(errorMessages.join(" "));
      } else {
        setErrorMsg(errorDetail || "회원가입에 실패했습니다.");
      }
    }
  };

  return (
    <div className={styles.page}>
      <form noValidate onSubmit={handleSubmit(onSubmit)} className={styles.card}>
        <img
          src="/simon_logo_48.png"
          srcSet="/simon_logo_48.png 1x, /simon_logo_96.png 2x, /simon_logo_144.png 3x"
          alt="Simon logo"
          className={styles.logo}
        />
        <h1 className={styles.title}>Simon-AI 회원가입</h1>
        <p className={styles.subtitle}>새 계정을 만들어 시작하세요.</p>

        {errorMsg && (
          <div role="alert" className={styles.alert}>{errorMsg}</div>
        )}

        {successMsg && (
          <div role="alert" className={styles.success}>{successMsg}</div>
        )}

        <div className={styles.nameRow}>
          <div className={styles.nameField}>
            <label htmlFor="lastName" className={styles.label}>성</label>
            <input
              id="lastName"
              type="text"
              placeholder="홍"
              {...register("lastName")}
              aria-invalid={!!errors.lastName}
              aria-describedby="lastName-error"
              className={`${styles.input} ${errors.lastName ? styles.isInvalid : ""}`}
            />
            {errors.lastName && (
              <div id="lastName-error" className={styles.errorText}>
                {errors.lastName.message?.toString()}
              </div>
            )}
          </div>

          <div className={styles.nameField}>
            <label htmlFor="firstName" className={styles.label}>이름</label>
            <input
              id="firstName"
              type="text"
              placeholder="길동"
              {...register("firstName")}
              aria-invalid={!!errors.firstName}
              aria-describedby="firstName-error"
              className={`${styles.input} ${errors.firstName ? styles.isInvalid : ""}`}
            />
            {errors.firstName && (
              <div id="firstName-error" className={styles.errorText}>
                {errors.firstName.message?.toString()}
              </div>
            )}
          </div>
        </div>

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

        <label htmlFor="username" className={styles.label}>닉네임 (선택사항)</label>
        <input
          id="username"
          type="text"
          placeholder="멋진 닉네임을 입력하세요"
          {...register("username")}
          aria-invalid={!!errors.username}
          aria-describedby="username-error"
          className={`${styles.input} ${errors.username ? styles.isInvalid : ""}`}
        />
        {errors.username && (
          <div id="username-error" className={styles.errorText}>
            {errors.username.message?.toString()}
          </div>
        )}

        <label htmlFor="password" className={styles.label}>비밀번호</label>
        <input
          id="password"
          type="password"
          autoComplete="new-password"
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

        <label htmlFor="passwordConfirm" className={styles.label}>비밀번호 확인</label>
        <input
          id="passwordConfirm"
          type="password"
          autoComplete="new-password"
          placeholder="********"
          {...register("passwordConfirm")}
          aria-invalid={!!errors.passwordConfirm}
          aria-describedby="passwordConfirm-error"
          className={`${styles.input} ${errors.passwordConfirm ? styles.isInvalid : ""}`}
        />
        {errors.passwordConfirm && (
          <div id="passwordConfirm-error" className={styles.errorText}>
            {errors.passwordConfirm.message?.toString()}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className={styles.submitBtn}
        >
          {isSubmitting ? "회원가입 중입니다..." : "회원가입"}
        </button>

        <div className={styles.linkContainer}>
          <p className={styles.linkText}>
            이미 계정이 있으신가요?{" "}
            <Link to="/login" className={styles.link}>
              로그인
            </Link>
          </p>
        </div>
      </form>
    </div>
  );
}
