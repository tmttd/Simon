import React, { useState, useEffect } from "react";
import styles from "./Sidebar.module.css";
import { api as apiClient } from "../../api/apiClient";

export default function Sidebar({
  selectedThreadId,
  onSelectThread,
  onNewChat,
}) {
  const [threads, setThreads] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchThreads = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.get("/chat/threads/");
        setThreads(response.data);
      } catch (err) {
        setError("대화 목록을 불러오는 데 실패했습니다.");
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchThreads();
  }, []);

  return (
    <div className={styles.sidebar}>
      <div className={styles.header}>
        <h2>대화 목록</h2>
        <button className={styles.newChatBtn} onClick={onNewChat}>
          + 새 대화
        </button>
      </div>
      <ul className={styles.threadList}>
        {isLoading && <li className={styles.loading}>로딩 중...</li>}
        {error && <li className={styles.error}>{error}</li>}
        {!isLoading &&
          !error &&
          threads.map((thread) => (
            <li
              key={thread.id}
              className={`${styles.threadItem} ${
                thread.id === selectedThreadId ? styles.selected : ""
              }`}
              onClick={() => onSelectThread(thread.id)}
            >
              {thread.title}
            </li>
          ))}
      </ul>
    </div>
  );
}
