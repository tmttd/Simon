import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { listStudySessions, getSessionDetail, deleteSession } from "../../api/apiClient";
import styles from "./GroupsDashboard.module.css";

export default function GroupsDashboard() {
  const [sessions, setSessions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const highlightId = location.state?.highlightGroupId || null;

  const fetchSessions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await listStudySessions();
      setSessions(list);
    } catch (e) {
      setError("세션 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchSessions(); }, []);

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
            <button className={styles.primaryBtn} onClick={() => navigate('/init-study')}>+ 새 학습 세션</button>
          </div>
        </div>
      {isLoading && <div className={styles.hint}>로딩 중…</div>}
      {error && <div className={styles.err}>{error}</div>}
        <div className={styles.grid}>
        {sessions.map((s) => (
          <div key={s.id} className={`${styles.card} ${highlightId === s.id ? styles.highlight : ''}`}>
              <div>
                <div className={styles.cardTitle}>{s.title}</div>
                <div className={styles.metaRow}>
                  <span className={styles.metaBadge}>스레드 {s.count ?? 0}</span>
                  {s.updated_at && (
                    <span className={styles.metaBadgeAlt} title={s.updated_at}>
                      업데이트 {new Date(s.updated_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
              <div className={styles.cardActions}>
                <button className={styles.secondaryBtn} onClick={() => handleOpen(s)}>열기</button>
                <button className={styles.dangerBtn} onClick={() => handleDelete(s)}>삭제</button>
              </div>
          </div>
        ))}
        </div>
      </div>
    </div>
  );
}


