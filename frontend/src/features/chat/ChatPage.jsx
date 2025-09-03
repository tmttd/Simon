import React, { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import ChatWindow from "./ChatWindow";
import styles from "./ChatPage.module.css";
import { api as apiClient } from "../../api/apiClient";

export default function ChatPage() {
  const { threadId } = useParams();
  const navigate = useNavigate();
  const [threads, setThreads] = useState([]);
  const [currentThreadId, setCurrentThreadId] = useState(threadId || null);

  const fetchThreads = useCallback(async () => {
    try {
      const response = await apiClient.get("/chat/threads/");
      setThreads(response.data);
    } catch (err) {
      console.error("대화 목록 조회 실패:", err);
      // 사용자에게 에러 알림 처리 추가 가능
    }
  }, []);

  // URL 파라미터가 변경될 때 currentThreadId 동기화
  useEffect(() => {
    setCurrentThreadId(threadId || null);
  }, [threadId]);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  const handleSelectThread = (threadId) => {
    navigate(`/chat/${threadId}`);
  };

  const handleNewChat = () => {
    navigate('/chat');
  };

  const onNewThreadStart = useCallback(
    (newThreadId) => {
      fetchThreads(); // 새 스레드가 생성되면 목록을 다시 불러옵니다.
      navigate(`/chat/${newThreadId}`);
    },
    [fetchThreads, navigate]
  );

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  const openSidebar = () => setIsSidebarOpen(true);
  const closeSidebar = () => setIsSidebarOpen(false);
  const handleSelectThreadWrapped = (tid) => {
    handleSelectThread(tid);
    closeSidebar();
  };

  return (
    <div className={styles.chatPage}>
      <div className={`${styles.sidebarWrapper} ${isSidebarOpen ? styles.open : ""}`}>
        <Sidebar
          threads={threads}
          setThreads={setThreads}
          selectedThreadId={currentThreadId}
          onSelectThread={handleSelectThreadWrapped}
          onNewChat={() => { handleNewChat(); closeSidebar(); }}
        />
      </div>

      <div className={styles.backdrop} onClick={closeSidebar} />

      <ChatWindow
        threadId={currentThreadId}
        onNewThreadStart={onNewThreadStart}
        onOpenMenu={openSidebar}
      />
    </div>
  );
}
