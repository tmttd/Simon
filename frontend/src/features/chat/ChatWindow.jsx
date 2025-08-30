import React from "react";
import styles from "./ChatWindow.module.css";

export default function ChatWindow() {
  const onSubmit = (e) => {
    e.preventDefault(); // 전송은 다음 단계에서 연결
  };

  return (
    <div className={styles.window}>
      <header className={styles.header}>
        <h1 className={styles.title}>Simon says</h1>
        <p className={styles.subtitle}>사이먼이 당신의 질문에 응답합니다.</p>
      </header>

      <main className={styles.main}>
        <div className={styles.messageList}>리스트</div>
      </main>

      <form onSubmit={onSubmit} className={styles.form}>
        <input
          type="text"
          placeholder="메세지를 입력하세요."
          className={styles.input}
        />
        <button type="submit" className={styles.submitBtn}>
          전송
        </button>
      </form>
    </div>
  );
}