import React, { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import Sidebar from "./Sidebar";
import ChatWindow from "./ChatWindow";
import styles from "./ChatPage.module.css";
import { getSessionDetail, listThreads } from "../../api/apiClient";

export default function ChatPage() {
  const { threadId, groupId: sessionId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [threads, setThreads] = useState([]);
  const [currentThreadId, setCurrentThreadId] = useState(threadId || null);
  const [initialExpandGroupId, setInitialExpandGroupId] = useState(null);
  const [stateSummary, setStateSummary] = useState(null);

  const fetchThreads = useCallback(async () => {
    try {
      if (sessionId) {
        const detail = await getSessionDetail(sessionId);
        setThreads(detail.threads || []);
      } else {
        const ungrouped = await listThreads({ ungrouped: true });
        setThreads(ungrouped);
      }
    } catch (err) {
      console.error("대화 목록 조회 실패:", err);
    }
  }, [sessionId]);

  // URL 파라미터가 변경될 때 currentThreadId 동기화
  useEffect(() => {
    setCurrentThreadId(threadId || null);
  }, [threadId]);

  useEffect(() => {
    const state = location.state;
    if (state && state.expandGroupId) {
      setInitialExpandGroupId(state.expandGroupId);
      // 일회성 사용 후 제거
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location, navigate]);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  const handleSelectThread = (tid) => {
    if (sessionId) navigate(`/session/${sessionId}/chat/${tid}`);
    else navigate(`/chat/${tid}`);
  };

  const handleNewChat = () => {
    if (sessionId) navigate(`/session/${sessionId}/chat`);
    else navigate('/chat');
  };

  const onNewThreadStart = useCallback(
    (newThreadId) => {
      fetchThreads(); // 새 스레드가 생성되면 목록을 다시 불러옵니다.
      if (sessionId) navigate(`/session/${sessionId}/chat/${newThreadId}`);
      else navigate(`/chat/${newThreadId}`);
    },
    [fetchThreads, navigate, sessionId]
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
        <div style={{ padding: 8 }}>
          <button onClick={() => navigate('/dashboard')} className={styles.toInitBtn}>
            대시보드로
          </button>
        </div>
        <Sidebar
          threads={threads}
          setThreads={setThreads}
          selectedThreadId={currentThreadId}
          onSelectThread={handleSelectThreadWrapped}
          onNewChat={() => { handleNewChat(); closeSidebar(); }}
          onRefresh={fetchThreads}
          stateSummary={stateSummary}
        />
      </div>

      <div className={styles.backdrop} onClick={closeSidebar} />

      <ChatWindow
        threadId={currentThreadId}
        groupId={sessionId}
        onNewThreadStart={onNewThreadStart}
        onOpenMenu={openSidebar}
        onStateUpdate={setStateSummary}
      />
    </div>
  );
}
