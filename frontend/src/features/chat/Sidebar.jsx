import React, { useState, useEffect, useRef } from "react";
import styles from "./Sidebar.module.css";
import { api as apiClient } from "../../api/apiClient";
import { DotsHorizontalIcon, PencilIcon, TrashIcon } from "./icons";

export default function Sidebar({
  selectedThreadId,
  onSelectThread,
  onNewChat,
  threads,
  setThreads, // ChatPage로부터 threads 상태와 setter를 props로 받음
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [renameText, setRenameText] = useState("");
  const renameInputRef = useRef(null);

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

  useEffect(() => {
    fetchThreads();
  }, []);

  useEffect(() => {
    if (editingThreadId && renameInputRef.current) {
      renameInputRef.current.focus();
    }
  }, [editingThreadId]);

  const handleStartRename = (thread) => {
    setEditingThreadId(thread.id);
    setRenameText(thread.title);
  };

  const handleCancelRename = () => {
    setEditingThreadId(null);
    setRenameText("");
  };

  const handleRename = async (e) => {
    e.preventDefault();
    if (!renameText.trim()) return;

    try {
      await apiClient.patch(`/chat/thread/${editingThreadId}/`, {
        title: renameText,
      });
      await fetchThreads(); // 목록 새로고침
    } catch (err) {
      console.error("이름 변경 실패:", err);
      // TODO: 사용자에게 에러 알림
    } finally {
      handleCancelRename();
    }
  };

  const handleDelete = async (threadId) => {
    if (window.confirm("정말로 이 대화를 삭제하시겠습니까?")) {
      try {
        await apiClient.delete(`/chat/thread/${threadId}/`);
        await fetchThreads(); // 목록 새로고침
        if (threadId === selectedThreadId) {
          onNewChat(); // 현재 선택된 대화가 삭제되면 새 대화 시작
        }
      } catch (err) {
        console.error("삭제 실패:", err);
        // TODO: 사용자에게 에러 알림
      }
    }
  };

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
              onClick={() => editingThreadId !== thread.id && onSelectThread(thread.id)}
            >
              {editingThreadId === thread.id ? (
                <form onSubmit={handleRename} onBlur={handleCancelRename} className={styles.renameForm}>
                  <input
                    ref={renameInputRef}
                    type="text"
                    value={renameText}
                    onChange={(e) => setRenameText(e.target.value)}
                    className={styles.renameInput}
                  />
                </form>
              ) : (
                <>
                  <span className={styles.threadTitle}>{thread.title}</span>
                  <div className={styles.actions}>
                    <button onClick={(e) => { e.stopPropagation(); handleStartRename(thread); }} className={styles.actionBtn}>
                      <PencilIcon />
                    </button>
                    <button onClick={(e) => { e.stopPropagation(); handleDelete(thread.id); }} className={styles.actionBtn}>
                      <TrashIcon />
                    </button>
                  </div>
                </>
              )}
            </li>
          ))}
      </ul>
    </div>
  );
}
