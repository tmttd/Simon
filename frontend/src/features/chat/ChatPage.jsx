import React, { useState, useCallback, useEffect } from "react";
import Sidebar from "./Sidebar";
import ChatWindow from "./ChatWindow";
import styles from "./ChatPage.module.css";
import { api as apiClient } from "../../api/apiClient";

export default function ChatPage() {
  const [threads, setThreads] = useState([]);
  const [currentThreadId, setCurrentThreadId] = useState(null);

  const fetchThreads = useCallback(async () => {
    try {
      const response = await apiClient.get("/chat/threads/");
      setThreads(response.data);
    } catch (err) {
      console.error("대화 목록 조회 실패:", err);
      // 사용자에게 에러 알림 처리 추가 가능
    }
  }, []);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  const handleSelectThread = (threadId) => {
    setCurrentThreadId(threadId);
  };

  const handleNewChat = () => {
    setCurrentThreadId(null);
  };

  const onNewThreadStart = useCallback(
    (newThreadId) => {
      fetchThreads(); // 새 스레드가 생성되면 목록을 다시 불러옵니다.
      setCurrentThreadId(newThreadId);
    },
    [fetchThreads]
  );

  return (
    <div className={styles.chatPage}>
      <Sidebar
        threads={threads}
        setThreads={setThreads}
        selectedThreadId={currentThreadId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
      />
      <ChatWindow
        key={currentThreadId}
        threadId={currentThreadId}
        onNewThreadStart={onNewThreadStart}
      />
    </div>
  );
}
