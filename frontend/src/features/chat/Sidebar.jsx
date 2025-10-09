import React, { useState, useEffect, useRef } from "react";
import styles from "./Sidebar.module.css";
import { api as apiClient, listThreads } from "../../api/apiClient";
import { DotsHorizontalIcon, PencilIcon, TrashIcon } from "./icons";

export default function Sidebar({
  selectedThreadId,
  onSelectThread,
  onNewChat,
  threads,
  setThreads, // ChatPage로부터 threads 상태와 setter를 props로 받음
  initialExpandGroupId,
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [renameText, setRenameText] = useState("");
  const renameInputRef = useRef(null);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState(new Set());

  const fetchThreads = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const ungrouped = await listThreads({ ungrouped: true });
      setThreads(ungrouped);
    } catch (err) {
      setError("대화 목록을 불러오는 데 실패했습니다.");
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleGroup = async (groupId) => {
    if (expandedGroupId === groupId) {
      setExpandedGroupId(null);
      return;
    }
    try {
      const detail = await getGroupDetail(groupId);
      setGroupThreads((prev) => ({ ...prev, [groupId]: detail.threads }));
      setExpandedGroupId(groupId);
    } catch (e) {
      console.error(e);
    }
  };

  const handleDeleteGroup = async (groupId) => {
    if (!window.confirm("이 그룹과 하위 대화를 모두 삭제할까요?")) return;
    try {
      await deleteGroup(groupId);
      if (expandedGroupId === groupId) setExpandedGroupId(null);
      await fetchThreads();
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, []);

  // initialExpandGroupId 미사용: 현재 페이지 컨텍스트로 목록을 제공

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
      if (expandedGroupId) {
        try {
          const detail = await getGroupDetail(expandedGroupId);
          setGroupThreads((prev) => ({ ...prev, [expandedGroupId]: detail.threads }));
        } catch (_) {}
      }
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

  const toggleSelect = (threadId) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(threadId)) next.delete(threadId);
      else next.add(threadId);
      return next;
    });
  };

  const handleCreateGroupFromOthers = async () => {
    if (!newGroupTitle.trim() || selectedIds.size === 0) return;
    try {
      const group = await createGroup(newGroupTitle.trim());
      const ops = Array.from(selectedIds).map((tid) => assignThreadToGroup(tid, group.id));
      await Promise.all(ops);
      setSelectionMode(false);
      setSelectedIds(new Set());
      setNewGroupTitle("");
      await fetchThreads();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className={styles.sidebar}>
      <div className={styles.header}>
        <h2>대화 목록</h2>
        <button className={styles.newChatBtn} onClick={onNewChat}>
          + 새 질문
        </button>
      </div>
      {/* 그룹화 기능 제거 */}
      <ul className={styles.threadList}>
        {isLoading && <li className={styles.loading}>로딩 중...</li>}
        {error && <li className={styles.error}>{error}</li>}
        {!isLoading && !error && threads.length > 0 && (
          <li className={styles.groupItem}>
            <ul className={styles.childList}>
              {threads.map((thread) => (
                <li
                  key={thread.id}
                  className={`${styles.threadItem} ${thread.id === selectedThreadId ? styles.selected : ""}`}
                  onClick={() => {
                    if (selectionMode) toggleSelect(thread.id);
                    else if (editingThreadId !== thread.id) onSelectThread(thread.id);
                  }}
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
                      <span className={styles.threadTitle}>
                        {selectionMode && (
                          <input
                            type="checkbox"
                            checked={selectedIds.has(thread.id)}
                            onChange={(e) => toggleSelect(thread.id)}
                            onClick={(e) => e.stopPropagation()}
                            style={{ marginRight: 8 }}
                          />
                        )}
                        {thread.title}
                      </span>
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
          </li>
        )}
      </ul>
    </div>
  );
}
