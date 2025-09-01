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

  const isNewChat = !threadId;

  // 초기 렌더링 상태인지 판단 (애니메이션 클래스 적용 기준)
  const isInitialView = isNewChat && messages.length === 0;

  useEffect(() => {
    if (isNewChat) {
      setMessages([]);
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
    setIsStreaming(true);
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

      if (isNewChat) {
        onNewThreadStart(newThreadId);
      }

      if (response.data && response.data.response) {
        const duration = (Date.now() - requestStartTimeRef.current) / 1000;
        
        // AI 메시지를 미리 추가 (타이핑 애니메이션용)
        const aiMessage = {
          sender: "ai",
          text: "",
          duration: 0,
        };
        setMessages((prev) => [...prev, aiMessage]);

        // 타이핑 애니메이션 시작
        await typeMessage(response.data.response, duration);
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
        // 실패한 AI 메시지 제거
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastMessage = newMessages[newMessages.length - 1];
          if (lastMessage && lastMessage.sender === "ai" && !lastMessage.text) {
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
    const delay = Math.max(10, Math.min(100, 2000 / chars.length)); // 10-100ms 사이로 조절
    
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

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    executeSend(input, threadId);
    setInput("");
  };

  const handleRetry = () => {
    if (error && error.originalText) {
      setMessages((prev) => prev.slice(0, -1));
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
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="메세지를 입력하세요."
        className={styles.input}
        disabled={isLoading}
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
          <div>
            <h1 className={styles.title}>Simon says</h1>
            <p className={styles.subtitle}>
              {user?.email
                ? `${user.email}님, 안녕하세요!`
                : "무엇이든 물어보세요!"}
            </p>
          </div>
          <button onClick={logout} className={styles.logoutBtn}>
            로그아웃
          </button>
        </header>
        <div className={styles.initialMain}>
          <div className={styles.welcome}>
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
        <div>
          <h1 className={styles.title}>Simon says</h1>
          <p className={styles.subtitle}>
            {user?.email
              ? `${user.email}님, 안녕하세요!`
              : "사이먼이 당신의 질문에 응답합니다."}
          </p>
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