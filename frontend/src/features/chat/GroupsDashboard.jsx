import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { listStudyGroups, getGroupDetail, deleteGroup } from "../../api/apiClient";
import styles from "./GroupsDashboard.module.css";

export default function GroupsDashboard() {
  const [groups, setGroups] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();
  const highlightId = location.state?.highlightGroupId || null;

  const fetchGroups = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const list = await listStudyGroups();
      setGroups(list);
    } catch (e) {
      setError("그룹 목록을 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchGroups(); }, []);

  const handleOpen = async (g) => {
    try {
      const detail = await getGroupDetail(g.id);
      const first = (detail.threads || [])[0];
      if (first) navigate(`/group/${g.id}/chat/${first.id}`);
      else navigate(`/group/${g.id}/chat`);
    } catch (e) {
      navigate(`/group/${g.id}/chat`);
    }
  };

  const handleDelete = async (g) => {
    if (!window.confirm("이 그룹과 하위 대화를 모두 삭제할까요?")) return;
    try {
      await deleteGroup(g.id);
      fetchGroups();
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
        {groups.map((g) => (
          <div key={g.id} className={`${styles.card} ${highlightId === g.id ? styles.highlight : ''}`}>
              <div>
                <div className={styles.cardTitle}>{g.title}</div>
                <div className={styles.metaRow}>
                  <span className={styles.metaBadge}>스레드 {g.count ?? 0}</span>
                  {g.updated_at && (
                    <span className={styles.metaBadgeAlt} title={g.updated_at}>
                      업데이트 {new Date(g.updated_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
              <div className={styles.cardActions}>
                <button className={styles.secondaryBtn} onClick={() => handleOpen(g)}>열기</button>
                <button className={styles.dangerBtn} onClick={() => handleDelete(g)}>삭제</button>
              </div>
          </div>
        ))}
        </div>
      </div>
    </div>
  );
}


