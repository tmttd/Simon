import React, { useState, useCallback } from "react";
import Sidebar from "./Sidebar";
import ChatWindow from "./ChatWindow";
import styles from "./ChatPage.module.css";

export default function ChatPage() {
  const [currentThreadId, setCurrentThreadId] = useState(null);
  const [sidebarKey, setSidebarKey] = useState(Date.now()); // 사이드바 새로고침을 위한 key

  const handleSelectThread = (threadId) => {
    setCurrentThreadId(threadId);
  };

  const handleNewChat = () => {
    setCurrentThreadId(null);
  };

  // 새 대화가 시작되었을 때 호출될 콜백
  const onNewThreadStart = useCallback((newThreadId) => {
    setCurrentThreadId(newThreadId);
    // 사이드바를 강제로 다시 렌더링하여 새 대화 목록을 불러오도록 함
    setSidebarKey(Date.now());
  }, []);

  return (
    <div className={styles.chatPage}>
      <Sidebar
        key={sidebarKey}
        selectedThreadId={currentThreadId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
      />
      <ChatWindow
        key={currentThreadId} // threadId가 변경될 때마다 ChatWindow를 리마운트
        threadId={currentThreadId}
        onNewThreadStart={onNewThreadStart}
      />
    </div>
  );
}
