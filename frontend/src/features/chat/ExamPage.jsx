import React from "react";
import { useNavigate } from "react-router-dom";
import styles from "./ExamPage.module.css";

export default function ExamPage() {
  const navigate = useNavigate();

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <h1 className={styles.title}>열심히 개발 중입니다 🚀</h1>
        <button 
          className={styles.backBtn}
          onClick={() => navigate(-1)}
        >
          돌아가기
        </button>
      </div>
    </div>
  );
}

