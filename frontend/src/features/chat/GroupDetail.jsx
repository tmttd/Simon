import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { getGroupDetail } from "../../api/apiClient";
import styles from "./GroupDetail.module.css";

export default function GroupDetail() {
  const { groupId } = useParams();
  const [threads, setThreads] = useState([]);
  const [group, setGroup] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const fetchDetail = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getGroupDetail(groupId);
      setGroup(data.group);
      setThreads(data.threads || []);
    } catch (e) {
      setError("그룹 정보를 불러오지 못했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchDetail(); }, [groupId]);

  const startNewChat = () => {
    navigate(`/group/${groupId}/chat`);
  };

  const openThread = (t) => {
    navigate(`/group/${groupId}/chat/${t.id}`);
  };

  return (
    <div className={styles.page}>
      <div className={styles.topbar}>
        <h1 className={styles.title}>{group?.title || '그룹'}</h1>
        <div className={styles.actions}>
          <button className={styles.secondaryBtn} onClick={() => navigate('/dashboard')}>대시보드</button>
          <button className={styles.primaryBtn} onClick={startNewChat}>새 대화 시작</button>
        </div>
      </div>
      {isLoading && <div className={styles.hint}>로딩 중…</div>}
      {error && <div className={styles.err}>{error}</div>}
      <ul className={styles.list}>
        {threads.map((t) => (
          <li key={t.id} className={styles.item} onClick={() => openThread(t)}>
            <span className={styles.itemTitle}>{t.title}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}


