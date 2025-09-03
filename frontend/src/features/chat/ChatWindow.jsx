import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { v4 as uuidv4 } from "uuid";
import { api as apiClient } from "../../api/apiClient";
import { useAuth } from "../../context/AuthContext";
import styles from "./ChatWindow.module.css";
import { PaperAirplaneIcon, StopIcon, RetryIcon } from "./icons.jsx";

export default function ChatWindow({ threadId, onNewThreadStart }) {
  const { user, logout } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false); // 스트리밍 상태 추가
  const [, setNow] = useState(null); // For re-rendering during loading
  const [error, setError] = useState(null);
  const mainRef = useRef(null);
  const abortControllerRef = useRef(null);
  const requestStartTimeRef = useRef(null);
  const skipHistoryForThreadRef = useRef(null); // 방금 생성한 스레드의 초기 히스토리 fetch를 1회 건너뛰기 위한 플래그

  const isNewChat = !threadId;

  // 초기 렌더링 상태인지 판단 (애니메이션 클래스 적용 기준)
  const isInitialView = isNewChat && messages.length === 0;

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
      setIsLoading(true);
      setError(null);
      try {
        const response = await apiClient.get(`/chat/history/${threadId}/`);
        if (response.data && Array.isArray(response.data.history)) {
          setMessages(response.data.history);
        }
      } catch (error) {
        console.error("채팅 기록을 불러오는 데 실패했습니다.", error);
        setError({ message: "채팅 기록을 불러오는 데 실패했습니다." });
      } finally {
        setIsLoading(false);
      }
    };

    fetchHistory();
  }, [threadId, isNewChat]);

  useEffect(() => {
    if (mainRef.current) {
      mainRef.current.scrollTop = mainRef.current.scrollHeight;
    }
  }, [messages, isLoading, error]);

  useEffect(() => {
    if (!isLoading) return;

    let frameId;
    const frame = () => {
      setNow(Date.now());
      frameId = requestAnimationFrame(frame);
    };

    frameId = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(frameId);
    };
  }, [isLoading]);

  const executeSend = async (messageText, currentThreadId) => {
    setIsLoading(true);
    setIsStreaming(false); // 처음에는 로딩 상태 유지
    setError(null);
    abortControllerRef.current = new AbortController();
    requestStartTimeRef.current = Date.now();

    const newThreadId = isNewChat ? uuidv4() : currentThreadId;

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
        const duration = (Date.now() - requestStartTimeRef.current) / 1000;
        
        // API 응답을 받은 후 스트리밍 상태로 변경
        setIsStreaming(true);
        
        // AI 메시지를 미리 추가 (타이핑 애니메이션용)
        const aiMessage = {
          sender: "ai",
          text: "",
          duration: 0,
        };
        setMessages((prev) => [...prev, aiMessage]);

        // 타이핑 애니메이션 시작
        await typeMessage(response.data.response, duration);

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
          if (lastMessage && lastMessage.sender === "ai" && (!lastMessage.text || lastMessage.text === "")) {
            newMessages.pop();
          }
          return newMessages;
        });
      }
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  // 타이핑 애니메이션 함수
  const typeMessage = async (fullText, duration) => {
    const chars = fullText.split('');
    const TYPING_SPEED = 8; // 초당 글자 수 (원하는 속도로 조절 가능)
    const delay = 1000 / TYPING_SPEED; // 각 글자 간격 (ms)
    
    for (let i = 0; i <= chars.length; i++) {
      if (abortControllerRef.current?.signal.aborted) {
        break; // 중단된 경우 타이핑 중지
      }
      
      const currentText = chars.slice(0, i).join('');
      // 타이핑 중일 때는 커서를 텍스트에 직접 포함
      const displayText = i < chars.length ? currentText + '▋' : currentText;
      
      setMessages((prev) => {
        const newMessages = [...prev];
        const lastMessage = newMessages[newMessages.length - 1];
        if (lastMessage && lastMessage.sender === "ai") {
          lastMessage.text = displayText;
          lastMessage.isTyping = i < chars.length; // 타이핑 상태 추가
          if (i === chars.length) {
            lastMessage.duration = duration; // 타이핑 완료 시 duration 설정
            lastMessage.isTyping = false;
          }
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
        const normalize = (arr) => arr.map((m) => ({
          sender: m.sender,
          text: (m.text || "").replace(/▋$/, ""),
        }));

        const prevNorm = normalize(prev);
        const serverNorm = normalize(serverHistory);

        // 앞부분 동일하고 서버가 더 길면, 부족한 뒤쪽만 추가
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
          }));
          return [...prev, ...toAppend];
        }

        // 길이 같고 마지막 하나만 다르면 마지막만 교체(덜 깜빡이게)
        if (
          prevNorm.length === serverNorm.length &&
          prevNorm.length > 0 &&
          i === prevNorm.length - 1
        ) {
          const updated = [...prev];
          const last = { ...updated[updated.length - 1] };
          last.text = serverHistory[serverHistory.length - 1].text || "";
          last.isTyping = false;
          updated[updated.length - 1] = last;
          return updated;
        }

        // 완전히 동일하거나 서버가 짧거나 초반 불일치면 그대로 둠(덮어쓰기 회피)
        return prev;
      });
    } catch (e) {
      console.error("히스토리 동기화 실패:", e);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

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
        if (!input.trim() || isLoading) return;
        
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
        disabled={isLoading}
        rows={1}
      />
      <button
        type={isLoading ? "button" : "submit"}
        className={styles.submitBtn}
        onClick={isLoading ? handleStop : undefined}
        disabled={!input.trim() && !isLoading}
      >
        {isLoading ? (
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
          {isLoading && !isStreaming && requestStartTimeRef.current && (
            <div className={`${styles.message} ${styles.aiMessage}`}>
              <div className={styles.loadingContainer}>
                <div className={styles.spinner}></div>
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