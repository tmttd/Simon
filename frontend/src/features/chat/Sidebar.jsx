import React, { useEffect, useRef, useState } from "react";
import styles from "./Sidebar.module.css";

export default function Sidebar({
  onNewChat,
  stateSummary, // { subject, learning_paths:[{title,completed}], current_path_index }
}) {
  const [justCompletedIndices, setJustCompletedIndices] = useState(new Set());
  const prevPathsRef = useRef([]);

  // 새로 완료된 항목 감지
  useEffect(() => {
    if (!stateSummary?.learning_paths) return;
    
    const currentPaths = stateSummary.learning_paths;
    const prevPaths = prevPathsRef.current;
    
    const newlyCompleted = new Set();
    currentPaths.forEach((lp, idx) => {
      const wasCompleted = prevPaths[idx]?.completed;
      const isCompleted = lp.completed;
      // 이전에는 완료되지 않았는데 지금 완료됨
      if (!wasCompleted && isCompleted) {
        newlyCompleted.add(idx);
      }
    });
    
    if (newlyCompleted.size > 0) {
      setJustCompletedIndices(newlyCompleted);
      // 2초 후 애니메이션 클래스 제거
      setTimeout(() => {
        setJustCompletedIndices(new Set());
      }, 2000);
    }
    
    prevPathsRef.current = currentPaths;
  }, [stateSummary?.learning_paths]);

  const Checklist = () => {
    if (!stateSummary) return null;
    const { subject, learning_paths = [], current_path_index } = stateSummary;
    return (
      <div className={styles.checklistCard}>
        <div className={styles.checklistHeader}>
          <div className={styles.subjectTitle}>{subject || "학습 진행"}</div>
        </div>
        <ul className={styles.pathsList}>
          {learning_paths.map((lp, idx) => {
            const done = !!lp.completed;
            const isJustCompleted = justCompletedIndices.has(idx);
            return (
              <li key={idx} className={styles.pathRow} title={lp.title}>
                <span className={`${styles.pathCheck} ${done ? styles.pathCheckDone : ''} ${isJustCompleted ? styles.celebrate : ''}`}>
                  {done ? '✓' : ''}
                </span>
                <span className={styles.pathText}>{lp.title}</span>
                {idx === current_path_index && <span className={styles.currentBadge}>진행중</span>}
              </li>
            );
          })}
        </ul>
      </div>
    );
  };

  return (
    <div className={styles.sidebar}>
      <div className={styles.header}>
        <h2>학습 목표</h2>
      </div>

      <Checklist />
    </div>
  );
}
