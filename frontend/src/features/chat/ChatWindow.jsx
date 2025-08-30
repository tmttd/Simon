import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api as apiClient } from "../../api/apiClient";
import { useAuth } from "../../context/AuthContext";
import styles from "./ChatWindow.module.css";

export default function ChatWindow() {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const threadId = "test_1"; // 임시 스레드 ID
  const mainRef = useRef(null); // Ref 이름을 좀 더 명확하게 변경합니다.

  // 컴포넌트 마운트 시 채팅 기록 불러오기
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiClient.get(`/chat/history/${threadId}/`);
        // `history` 키의 값인 배열을 상태로 설정합니다.
        if (response.data && Array.isArray(response.data.history)) {
          setMessages(response.data.history);
        }
      } catch (error) {
        console.error("채팅 기록을 불러오는 데 실패했습니다.", error);
      }
    };

    fetchHistory();
  }, [threadId]);

  // 메시지 목록이 변경될 때마다 맨 아래로 스크롤합니다.
  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.scrollTop = mainRef.current.scrollHeight;
    }
  }, [messages]);


  const onSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await apiClient.post("/chat/ask/", {
        message: input,
        thread_id: threadId,
      });

      if (response.data && response.data.response) {
        const aiMessage = { sender: "ai", text: response.data.response };
        setMessages((prev) => [...prev, aiMessage]);
      }
    } catch (error) {
      console.error("메시지 전송에 실패했습니다.", error);
      const errorMessage = {
        sender: "ai",
        text: "메시지 전송 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <div className={styles.window}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Simon says</h1>
          <p className={styles.subtitle}>
            {user?.email ? `${user.email}님, 안녕하세요!` : "사이먼이 당신의 질문에 응답합니다."}
          </p>
        </div>
        <button onClick={logout} className={styles.logoutBtn}>
          로그아웃
        </button>
      </header>

      <main ref={mainRef} className={styles.main}>
        <div className={styles.messageList}>
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`${styles.message} ${
                msg.sender === "user" ? styles.userMessage : styles.aiMessage
              }`}
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.text}
              </ReactMarkdown>
            </div>
          ))}
        </div>
      </main>

      <form onSubmit={onSubmit} className={styles.form}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
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