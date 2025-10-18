import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { listStudySessions, getSessionDetail, deleteSession, getChatState } from "../../api/apiClient";
import styles from "./GroupsDashboard.module.css";

export default function GroupsDashboard() {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [animateHighlight, setAnimateHighlight] = useState(false);
  const [sessionStates, setSessionStates] = useState({}); // sessionId -> learning_paths 정보
  const navigate = useNavigate();
  const location = useLocation();
  const highlightId = location.state?.highlightGroupId || null;

  const fetchSessions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await listStudySessions();
      setSessions(list);
      
      // 각 세션의 학습 목표 정보 가져오기
      const statesMap = {};
      await Promise.all(
        list.map(async (session) => {
          try {
            // 세션의 첫 번째 스레드 정보 가져오기
            const detail = await getSessionDetail(session.id);
            const firstThread = detail.threads?.[0];
            
            if (firstThread) {
              // 첫 번째 스레드의 state 가져오기
              const state = await getChatState(firstThread.id);
              if (state?.learning_paths) {
                const total = state.learning_paths.length;
                const completed = state.learning_paths.filter(lp => lp.completed).length;
                const sessionFinished = !!state.session_finished;
                statesMap[session.id] = { completed, total, sessionFinished };
              }
            }
          } catch (e) {
            // 개별 세션 state 조회 실패는 무시
          }
        })
      );
      setSessionStates(statesMap);
    } catch (e) {
      setError("세션 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchSessions(); }, []);

  // 새로 생성된 세션 강조 애니메이션 (세션 로드 후 트리거)
  useEffect(() => {
    if (highlightId && sessions.length > 0 && !isLoading) {
      // 세션이 실제로 존재하는지 확인
      const targetExists = sessions.some(s => s.id === highlightId);
      
      if (targetExists) {
        // 약간의 딜레이 후 애니메이션 시작 (렌더링 완료 보장)
        const startTimer = setTimeout(() => {
          setAnimateHighlight(true);
        }, 100);
        
        const endTimer = setTimeout(() => {
          setAnimateHighlight(false);
        }, 2100); // 100ms 시작 딜레이 + 2000ms 애니메이션
        
        return () => {
          clearTimeout(startTimer);
          clearTimeout(endTimer);
        };
      }
    }
  }, [highlightId, sessions, isLoading]);

  const handleOpen = async (s) => {
    try {
      const detail = await getSessionDetail(s.id);
      const first = (detail.threads || [])[0];
      if (first) navigate(`/session/${s.id}/chat/${first.id}`);
      else navigate(`/session/${s.id}/chat`);
    } catch (e) {
      navigate(`/session/${s.id}/chat`);
    }
  };

  const handleDelete = async (s) => {
    if (!window.confirm("이 세션과 하위 대화를 모두 삭제할까요?")) return;
    try {
      await deleteSession(s.id);
      fetchSessions();
    } catch (e) {}
  };

  return (
    <div className={styles.page}>
      <div className={styles.board}>
        <div className={styles.topbar}>
          <div className={styles.brandWrap}>
            <img
              src="/simon_logo_32.png"
              srcSet="/simon_logo_32.png 1x, /simon_logo_64.png 2x, /simon_logo_96.png 3x"
              alt="Simon logo"
              className={styles.brandLogo}
            />
            <h1 className={styles.title}>Simon 학습 대시보드</h1>
          </div>
          <div className={styles.topActions}>
            <button className={styles.primaryBtn} onClick={() => navigate('/start')}>+ 새 학습 세션</button>
          </div>
        </div>
      {isLoading && <div className={styles.hint}>로딩 중…</div>}
      {error && <div className={styles.err}>{error}</div>}
        <div className={styles.grid}>
        {sessions.map((s) => {
          const isHighlighted = highlightId === s.id;
          const shouldCelebrate = isHighlighted && animateHighlight;
          const stateInfo = sessionStates[s.id];
          const isCompleted = stateInfo?.sessionFinished;
          
          return (
          <div key={s.id} className={`${styles.card} ${isHighlighted ? styles.highlight : ''} ${shouldCelebrate ? styles.celebrate : ''} ${isCompleted ? styles.completed : ''}`}>
              {isCompleted && (
                <div className={styles.completedStar}>⭐</div>
              )}
              <div>
                <div className={styles.cardTitle}>{s.title}</div>
                <div className={styles.metaRow}>
                  {stateInfo ? (
                    <div className={styles.progressDots}>
                      {Array.from({ length: stateInfo.total }, (_, i) => (
                        <span 
                          key={i} 
                          className={`${styles.dot} ${i < stateInfo.completed ? styles.dotCompleted : styles.dotPending}`}
                          title={`학습 목표 ${i + 1}/${stateInfo.total}`}
                        />
                      ))}
                    </div>
                  ) : (
                    <span className={styles.metaBadge}>로딩중...</span>
                  )}
                  {s.created_at && (
                    <span className={styles.metaBadgeAlt} title={s.created_at}>
                      생성시간 {new Date(s.created_at).toLocaleString('ko-KR', { 
                        year: 'numeric', 
                        month: 'numeric', 
                        day: 'numeric', 
                        hour: 'numeric', 
                        minute: 'numeric',
                        hour12: true 
                      })}
                    </span>
                  )}
                </div>
              </div>
              <div className={styles.cardActions}>
                <button className={styles.examBtn} onClick={() => navigate(`/exam/${s.id}`)}>📝 수능형 문제</button>
                <button className={styles.secondaryBtn} onClick={() => handleOpen(s)}>열기</button>
                <button className={styles.dangerBtn} onClick={() => handleDelete(s)}>삭제</button>
              </div>
          </div>
          );
        })}
        </div>
      </div>
    </div>
  );
}


