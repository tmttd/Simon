import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { v4 as uuidv4 } from "uuid";
import { api as apiClient, getChatState } from "../../api/apiClient";
import { useAuth } from "../../context/AuthContext";
import styles from "./ChatWindow.module.css";
import { PaperAirplaneIcon, StopIcon, RetryIcon } from "./icons.jsx";

export default function ChatWindow({ threadId, groupId, onNewThreadStart, onOpenMenu, onStateUpdate }) {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false); // 스트리밍 상태 추가
  const [isFetchingHistory, setIsFetchingHistory] = useState(false);
  const [, setNow] = useState(null); // For re-rendering during loading
  const [error, setError] = useState(null);
  const [pendingUserText, setPendingUserText] = useState(null);
  const [fadeOutOldPair, setFadeOutOldPair] = useState(false);
  const [visiblePair, setVisiblePair] = useState({ userText: null, aiText: null, aiDuration: 0, fadeIn: false, aiIsIndicator: false });
  const fadeOutTimeoutRef = useRef(null);
  const mainRef = useRef(null);
  const abortControllerRef = useRef(null);
  const requestStartTimeRef = useRef(null);
  const pendingThreadIdRef = useRef(null);
  const skipHistoryForThreadRef = useRef(null); // 방금 생성한 스레드의 초기 히스토리 fetch를 1회 건너뛰기 위한 플래그
  const currentThreadIdRef = useRef(threadId);
  const threadStatusRef = useRef({});

  // 새로 추가된 상태는 상위로 올림: ChatPage가 Sidebar에 전달
  const reportState = (summary) => {
    try { if (onStateUpdate) onStateUpdate(summary); } catch (_) {}
  };

  const isNewChat = !threadId;
  const isBusy = isSending || isFetchingHistory;

  

  const getStatusKey = (tid) => (tid == null ? "__new__" : tid);

  const getLatestPairFrom = (arr) => {
    if (!Array.isArray(arr) || arr.length === 0) return { userText: null, aiText: null, aiDuration: 0 };
    let aiIndex = -1;
    for (let i = arr.length - 1; i >= 0; i--) {
      const m = arr[i];
      if (m.sender === "ai" && (m.text || "").length > 0) { aiIndex = i; break; }
    }
    if (aiIndex === -1) return { userText: null, aiText: null, aiDuration: 0 };
    let userIndex = -1;
    for (let j = aiIndex - 1; j >= 0; j--) {
      const m = arr[j];
      if (m.sender === "user") { userIndex = j; break; }
    }
    return {
      userText: userIndex !== -1 ? (arr[userIndex].text || null) : null,
      aiText: arr[aiIndex].text || null,
      aiDuration: Number(arr[aiIndex].duration || 0),
    };
  };

  const updateThreadStatus = (tid, updates) => {
    const key = getStatusKey(tid);
    const prevStatus = threadStatusRef.current[key] || {};
    const nextStatus = { ...prevStatus, ...updates };
    threadStatusRef.current[key] = nextStatus;

    if (key === getStatusKey(currentThreadIdRef.current)) {
      if ("isSending" in updates) {
        setIsSending(!!nextStatus.isSending);
      }
      if ("isStreaming" in updates) {
        setIsStreaming(!!nextStatus.isStreaming);
      }
      if ("requestStartTime" in updates) {
        requestStartTimeRef.current =
          updates.requestStartTime != null ? updates.requestStartTime : null;
      }
    }

    return nextStatus;
  };

  useEffect(() => {
    currentThreadIdRef.current = threadId;
    const status = threadStatusRef.current[getStatusKey(threadId)] || {};
    setIsSending(!!status.isSending);
    setIsStreaming(!!status.isStreaming);
    requestStartTimeRef.current = status.requestStartTime ?? null;
  }, [threadId]);

  // 스레드 변경 시 상태 요약 조회
  useEffect(() => {
    const fetchState = async () => {
      if (!threadId) { reportState(null); return; }
      try {
        const summary = await getChatState(threadId);
        reportState(summary || null);
      } catch (e) {
        // 상태 조회 실패는 치명적이지 않으므로 콘솔만
        console.warn("상태 조회 실패", e);
      }
    };
    fetchState();
  }, [threadId]);

  useEffect(() => {
    if (isNewChat) {
      setMessages([]);
      return;
    }

    // 방금 생성한 스레드라면, 초기 히스토리 요청 1회 건너뛰기 (타이핑 애니메이션 보존)
    if (skipHistoryForThreadRef.current === threadId) {
      skipHistoryForThreadRef.current = null;
      return;
    }

    const fetchHistory = async () => {
      setIsFetchingHistory(true);
      setError(null);
      try {
        const response = await apiClient.get(`/chat/history/${threadId}/`);
        if (response.data && Array.isArray(response.data.history)) {
          const serverHistory = response.data.history;
          setMessages((prev) => {
            if (threadId !== currentThreadIdRef.current) {
              return prev;
            }
            return serverHistory.map((message) => ({
              ...message,
              threadId,
              isTyping: false,
            }));
          });
          const pair = getLatestPairFrom(serverHistory);
          setVisiblePair({ userText: pair.userText, aiText: pair.aiText, aiDuration: pair.aiDuration, fadeIn: false, aiIsIndicator: false });

          // 완료 판정: 마지막 항목이 ai이고 text가 존재하면 완료로 간주
          const last = serverHistory[serverHistory.length - 1];
          const isComplete = !!last && last.sender === "ai" && !!(last.text && last.text.length > 0);
          if (isComplete) {
            updateThreadStatus(threadId, {
              isSending: false,
              isStreaming: false,
              requestStartTime: null,
            });
          }
        }
      } catch (error) {
        console.error("채팅 기록을 불러오는 데 실패했습니다.", error);
        setError({ message: "채팅 기록을 불러오는 데 실패했습니다." });
      } finally {
        setIsFetchingHistory(false);
      }
    };

    fetchHistory();
  }, [threadId, isNewChat]);

  // 자동 스크롤 비활성화 - 사용자가 직접 스크롤 위치 제어
  // useEffect(() => {
  //   if (mainRef.current) {
  //     mainRef.current.scrollTop = mainRef.current.scrollHeight;
  //   }
  // }, [messages, isBusy, error]);

  useEffect(() => {
    if (!isSending) return;

    let frameId;
    const frame = () => {
      setNow(Date.now());
      frameId = requestAnimationFrame(frame);
    };

    frameId = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [isSending]);

  const executeSend = async (messageText, currentThreadId) => {
    const newThreadId = isNewChat ? uuidv4() : currentThreadId;
    const requestStartTime = Date.now();
    updateThreadStatus(newThreadId, {
      isSending: true,
      isStreaming: false,
      requestStartTime,
    });
    if (getStatusKey(newThreadId) === getStatusKey(currentThreadIdRef.current)) {
      requestStartTimeRef.current = requestStartTime;
    }
    setError(null);
    abortControllerRef.current = new AbortController();
    pendingThreadIdRef.current = newThreadId;

    try {
      const response = await apiClient.post(
        "/chat/ask/",
        {
          message: messageText,
          thread_id: newThreadId,
          session_id: groupId || null,
        },
        {
          signal: abortControllerRef.current.signal,
        }
      );

      if (response.data && response.data.response) {
        const storedRequestStart = threadStatusRef.current[getStatusKey(newThreadId)]?.requestStartTime;
        const duration = storedRequestStart ? (Date.now() - storedRequestStart) / 1000 : 0;

        // 전체 응답을 수신한 뒤 페이드인으로 한 번에 표시
        const aiMessage = {
          sender: "ai",
          text: response.data.response,
          duration,
          threadId: newThreadId,
          isTyping: false,
          fadeIn: true,
        };
        // 타이머가 아직 유효하면 취소 (페이드아웃 완료 후 인디케이터 세팅되는 타이밍이 응답과 경합하지 않게)
        if (fadeOutTimeoutRef.current) { clearTimeout(fadeOutTimeoutRef.current); fadeOutTimeoutRef.current = null; }

        // messageText 파라미터를 사용 (상태값이 아닌 함수 호출 시점의 값 사용)
        const currentUserText = messageText;
        setMessages((prev) => {
          const next = [...prev];
          if (currentUserText) next.push({ sender: 'user', text: currentUserText });
          next.push(aiMessage);
          return next;
        });
        // visiblePair: 인디케이터에서 실제 응답으로 교체 + 페이드인
        setFadeOutOldPair(false);
        setVisiblePair({ userText: currentUserText, aiText: response.data.response, aiDuration: duration, fadeIn: true, aiIsIndicator: false });

        // 스트리밍 종료 후 상태 동기화 (체크리스트 최신화)
        try {
          const summary = await getChatState(newThreadId);
          reportState(summary || null);
        } catch (e) {
          console.warn("상태 동기화 실패", e);
        }

        // 스트리밍 완료 후 백그라운드 동기화로 깜빡임 없이 서버 기록 반영
        await fetchAndMergeHistory(newThreadId);

        // 새 스레드 라우팅은 타이핑이 끝난 뒤에 수행하여 리마운트/깜빡임 방지
        if (isNewChat) {
          // 첫 히스토리 fetch 1회 스킵해 애니메이션 결과가 덮어쓰이지 않게 함
          skipHistoryForThreadRef.current = newThreadId;
          onNewThreadStart(newThreadId);
        }

        // 응답 수신 후 오버레이 초기화
        setPendingUserText(null);
      }
    } catch (err) {
      if (err.name === "CanceledError") {
        console.log("Request canceled by user.");
      } else {
        console.error("메시지 전송에 실패했습니다.", err);
        setError({
          message: "메시지 전송 중 오류가 발생했습니다.",
          originalText: messageText,
        });
        // 실패한 빈 AI 메시지가 있다면 제거
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (
            lastMessage &&
            lastMessage.sender === "ai" &&
            lastMessage.threadId === pendingThreadIdRef.current &&
            (!lastMessage.text || lastMessage.text === "")
          ) {
            newMessages.pop();
          }
          return newMessages;
        });
      }
    } finally {
      pendingThreadIdRef.current = null;
      updateThreadStatus(newThreadId, {
        isSending: false,
        isStreaming: false,
        requestStartTime: null,
      });
      abortControllerRef.current = null;
    }
  };

  // 타이핑 애니메이션 함수 (비활성화)
  // const typeMessage = async (fullText, duration, targetThreadId) => { /* disabled */ };

  // 스트리밍 종료 후 서버 히스토리를 백그라운드로 가져와 현재 메시지와 깜빡임 없이 병합
  const fetchAndMergeHistory = async (tid) => {
    try {
      const response = await apiClient.get(`/chat/history/${tid}/`);
      const serverHistory = response.data && Array.isArray(response.data.history) ? response.data.history : [];

      setMessages((prev) => {
        if (tid !== currentThreadIdRef.current) {
          return prev;
        }

        const normalize = (arr) =>
          arr.map((m) => ({
            sender: m.sender,
            text: (m.text || "").replace(/▋$/, ""),
          }));

        const prevNorm = normalize(prev);
        const serverNorm = normalize(serverHistory);

        let i = 0;
        while (
          i < prevNorm.length &&
          i < serverNorm.length &&
          prevNorm[i].sender === serverNorm[i].sender &&
          prevNorm[i].text === serverNorm[i].text
        ) {
          i++;
        }

        if (i === prevNorm.length && serverNorm.length > prevNorm.length) {
          const toAppend = serverHistory.slice(prev.length).map((m) => ({
            sender: m.sender,
            text: m.text || "",
            duration: 0,
            isTyping: false,
            threadId: tid,
          }));
          return [...prev, ...toAppend];
        }

        if (
          prevNorm.length === serverNorm.length &&
          prevNorm.length > 0 &&
          i === prevNorm.length - 1
        ) {
          const updated = [...prev];
          const last = { ...updated[updated.length - 1] };
          last.text = serverHistory[serverHistory.length - 1].text || "";
          last.isTyping = false;
          last.threadId = tid;
          updated[updated.length - 1] = last;
          return updated;
        }

        // 완료 판정: 마지막 항목이 ai이고 text가 존재하면 완료로 간주
        const last = serverHistory[serverHistory.length - 1];
        const isComplete = !!last && last.sender === "ai" && !!(last.text && last.text.length > 0);
        if (isComplete) {
          updateThreadStatus(tid, {
            isSending: false,
            isStreaming: false,
            requestStartTime: null,
          });
        }

        return prev;
      });
    } catch (e) {
      console.error("히스토리 동기화 실패:", e);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isBusy) return;

    setPendingUserText(input);
    setFadeOutOldPair(true);
    // 페이드아웃 후 새 쌍으로 교체
    if (fadeOutTimeoutRef.current) { clearTimeout(fadeOutTimeoutRef.current); }
    fadeOutTimeoutRef.current = setTimeout(() => {
      setFadeOutOldPair(false);
      setVisiblePair({ userText: input, aiText: null, aiDuration: 0, fadeIn: false, aiIsIndicator: true });
    }, 450);
    executeSend(input, threadId);
    setInput("");
    // textarea 높이 초기화
    const textarea = e.target.querySelector('textarea');
    if (textarea) {
      textarea.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      if (e.ctrlKey || e.metaKey) {
        // Ctrl+Enter 또는 Cmd+Enter: 전송
        e.preventDefault();
        if (!input.trim() || isBusy) return;
        
        setPendingUserText(input);
        setFadeOutOldPair(true);
        // 페이드아웃 후 새 쌍으로 교체
        if (fadeOutTimeoutRef.current) { clearTimeout(fadeOutTimeoutRef.current); }
        fadeOutTimeoutRef.current = setTimeout(() => {
          setFadeOutOldPair(false);
          setVisiblePair({ userText: input, aiText: null, aiDuration: 0, fadeIn: false, aiIsIndicator: true });
        }, 450);
        executeSend(input, threadId);
        setInput("");
        // textarea 높이 초기화
        e.target.style.height = 'auto';
      }
      // Enter만 누르면: 줄바꿈 (기본 동작)
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    // 자동 높이 조절
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const handleRetry = () => {
    if (error && error.originalText) {
      // 오류 상태만 초기화하고, 메시지는 executeSend에서 처리
      setError(null);
      executeSend(error.originalText, threadId);
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setPendingUserText(null);
    setFadeOutOldPair(false);
    if (fadeOutTimeoutRef.current) { clearTimeout(fadeOutTimeoutRef.current); }
    // 이전 메시지 기록 기준으로 visiblePair 복구
    const pair = getLatestPairFrom(messages);
    setVisiblePair({ userText: pair.userText, aiText: pair.aiText, aiDuration: pair.aiDuration, fadeIn: false, aiIsIndicator: false });
  };

  const chatForm = (
    <form onSubmit={onSubmit} className={styles.form}>
      <textarea
        value={input}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        placeholder="메세지를 입력하세요. (Ctrl+Enter: 전송)"
        className={styles.input}
        disabled={isBusy}
        rows={1}
      />
      <button
        type={isSending ? "button" : "submit"}
        className={styles.submitBtn}
        onClick={isSending ? handleStop : undefined}
        disabled={(isFetchingHistory && !isSending) || (!input.trim() && !isSending)}
      >
        {isSending ? (
          <>
            <StopIcon className={styles.icon} />
            <span>중지</span>
          </>
        ) : (
          <>
            <span>Ctrl + ↵</span>
          </>
        )}
      </button>
    </form>
  );

  

  return (
    <div className={styles.window}>
      <header className={styles.header}>
        <button className={styles.mobileMenuBtn} onClick={onOpenMenu} aria-label="Open menu" />
        <div className={styles.brand}>
          <img
            src="/simon_logo_32.png"
            srcSet="/simon_logo_32.png 1x, /simon_logo_64.png 2x, /simon_logo_96.png 3x"
            alt="Simon logo"
            className={styles.logo}
          />
          <div>
            <h1 className={styles.title}>Simon says</h1>
            <p className={styles.subtitle}>
              {user?.email
                ? `${user.username || (user.first_name && user.last_name ? `${user.last_name}${user.first_name}` : user.email)}님, 안녕하세요!`
                : "사이먼이 당신의 질문에 응답합니다."}
            </p>
          </div>
        </div>
        <button onClick={logout} className={styles.logoutBtn}>
          로그아웃
        </button>
      </header>

      <main ref={mainRef} className={styles.main}>
        <div className={styles.messageList}>
          {visiblePair.userText && (
            <div className={`${styles.message} ${styles.userMessage} ${fadeOutOldPair ? styles.fadeOut : ''}`}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {visiblePair.userText}
              </ReactMarkdown>
            </div>
          )}

          <div className={`${styles.message} ${styles.aiMessage} ${(visiblePair.fadeIn && !fadeOutOldPair) ? styles.fadeIn : ''} ${fadeOutOldPair ? styles.fadeOut : ''}`}>
            {visiblePair.aiIsIndicator || !visiblePair.aiText ? (
              requestStartTimeRef.current ? (
                <div className={styles.loadingContainer}>
                  <div className={styles.loadingDots}>
                    <div></div>
                    <div></div>
                    <div></div>
                  </div>
                  <div className={styles.timer}>
                    {((Date.now() - requestStartTimeRef.current) / 1000).toFixed(1)}s
                  </div>
                </div>
              ) : null
            ) : (
              <>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {visiblePair.aiText}
                </ReactMarkdown>
                {visiblePair.aiDuration > 0 && (
                  <div className={styles.timer}>
                    {visiblePair.aiDuration.toFixed(1)}s
                  </div>
                )}
              </>
            )}
          </div>

          {error && (
            <div className={styles.errorMessage}>
              <span>{error.message}</span>
              {error.originalText && (
                <button onClick={handleRetry} className={styles.retryButton}>
                  <RetryIcon className={styles.icon} />
                  <span>재시도</span>
                </button>
              )}
            </div>
          )}
        </div>
      </main>

      {chatForm}
    </div>
  );
}