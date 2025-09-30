import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { v4 as uuidv4 } from "uuid";
import { api as apiClient } from "../../api/apiClient";
import { useAuth } from "../../context/AuthContext";
import styles from "./ChatWindow.module.css";
import { PaperAirplaneIcon, StopIcon, RetryIcon } from "./icons.jsx";

export default function ChatWindow({ threadId, onNewThreadStart, onOpenMenu }) {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false); // 스트리밍 상태 추가
  const [isFetchingHistory, setIsFetchingHistory] = useState(false);
  const [, setNow] = useState(null); // For re-rendering during loading
  const [error, setError] = useState(null);
  const mainRef = useRef(null);
  const abortControllerRef = useRef(null);
  const requestStartTimeRef = useRef(null);
  const pendingThreadIdRef = useRef(null);
  const skipHistoryForThreadRef = useRef(null); // 방금 생성한 스레드의 초기 히스토리 fetch를 1회 건너뛰기 위한 플래그
  const currentThreadIdRef = useRef(threadId);
  const threadStatusRef = useRef({});

  const isNewChat = !threadId;
  const isBusy = isSending || isFetchingHistory;

  // 초기 렌더링 상태인지 판단 (애니메이션 클래스 적용 기준)
  const isInitialView = isNewChat && messages.length === 0;

  const getStatusKey = (tid) => (tid == null ? "__new__" : tid);

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

  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.scrollTop = mainRef.current.scrollHeight;
    }
  }, [messages, isBusy, error]);

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
        },
        {
          signal: abortControllerRef.current.signal,
        }
      );

      if (response.data && response.data.response) {
        const storedRequestStart = threadStatusRef.current[getStatusKey(newThreadId)]?.requestStartTime;
        const duration = storedRequestStart ? (Date.now() - storedRequestStart) / 1000 : 0;
        
        // API 응답을 받은 후 스트리밍 상태로 변경
        updateThreadStatus(newThreadId, { isStreaming: true });
        
        // AI 메시지를 미리 추가 (타이핑 애니메이션용)
        const aiMessage = {
          sender: "ai",
          text: "",
          duration: 0,
          threadId: newThreadId,
        };
        setMessages((prev) => [...prev, aiMessage]);

        // 타이핑 애니메이션 시작
        await typeMessage(response.data.response, duration, newThreadId);

        // 스트리밍 완료 후 백그라운드 동기화로 깜빡임 없이 서버 기록 반영
        await fetchAndMergeHistory(newThreadId);

        // 새 스레드 라우팅은 타이핑이 끝난 뒤에 수행하여 리마운트/깜빡임 방지
        if (isNewChat) {
          // 첫 히스토리 fetch 1회 스킵해 애니메이션 결과가 덮어쓰이지 않게 함
          skipHistoryForThreadRef.current = newThreadId;
          onNewThreadStart(newThreadId);
        }
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

  // 타이핑 애니메이션 함수
  const typeMessage = async (fullText, duration, targetThreadId) => {
    const chars = fullText.split('');
    const TYPING_SPEED = 8; // 초당 글자 수 (원하는 속도로 조절 가능)
    const delay = 1000 / TYPING_SPEED; // 각 글자 간격 (ms)
    
    for (let i = 0; i <= chars.length; i++) {
      if (abortControllerRef.current?.signal.aborted) {
        break; // 중단된 경우 타이핑 중지
      }
      if (currentThreadIdRef.current !== targetThreadId) {
        break;
      }
      
      const currentText = chars.slice(0, i).join('');
      // 타이핑 중일 때는 커서를 텍스트에 직접 포함
      const displayText = i < chars.length ? currentText + '▋' : currentText;
      
      setMessages((prev) => {
        const newMessages = [...prev];
        let lastMessageIndex = -1;
        for (let idx = newMessages.length - 1; idx >= 0; idx--) {
          const msg = newMessages[idx];
          if (msg.sender === "ai" && msg.threadId === targetThreadId) {
            lastMessageIndex = idx;
            break;
          }
        }
        if (lastMessageIndex === -1) {
          return prev;
        }
        const lastMessage = newMessages[lastMessageIndex];
        lastMessage.text = displayText;
        lastMessage.isTyping = i < chars.length;
        if (i === chars.length) {
          lastMessage.duration = duration;
          lastMessage.isTyping = false;
        }
        return newMessages;
      });
      
      if (i < chars.length) {
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  };

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

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
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
        
        const userMessage = { sender: "user", text: input };
        setMessages((prev) => [...prev, userMessage]);
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
          <StopIcon className={styles.icon} />
        ) : (
          <PaperAirplaneIcon className={styles.icon} />
        )}
      </button>
    </form>
  );

  if (isInitialView) {
    return (
      <div className={`${styles.window} ${styles.initialLayout}`}>
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
                  : "무엇이든 물어보세요!"}
              </p>
            </div>
          </div>
          <button onClick={logout} className={styles.logoutBtn}>
            로그아웃
          </button>
        </header>
        <div className={styles.initialMain}>
          <div className={styles.welcome}>
            <img
              src="/simon_logo_48.png"
              srcSet="/simon_logo_48.png 1x, /simon_logo_96.png 2x, /simon_logo_144.png 3x"
              alt="Simon logo"
              className={styles.logoLarge}
            />
            <h1 className={styles.title}>무엇이든 물어보세요!</h1>
          </div>
          {chatForm}
        </div>
      </div>
    );
  }

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
              {msg.sender === "ai" && msg.duration > 0 && !msg.isTyping && (
                <div className={styles.timer}>
                  {msg.duration.toFixed(1)}s
                </div>
              )}
            </div>
          ))}
          {isSending && pendingThreadIdRef.current === threadId && !isStreaming && requestStartTimeRef.current && (
            <div className={`${styles.message} ${styles.aiMessage}`}>
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
            </div>
          )}
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