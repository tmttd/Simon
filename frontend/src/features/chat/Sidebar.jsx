import React from "react";
import styles from "./Sidebar.module.css";

export default function Sidebar({
  onNewChat,
  stateSummary, // { subject, learning_paths:[{title,completed}], current_path_index }
}) {
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
            return (
              <li key={idx} className={styles.pathRow} title={lp.title}>
                <span className={`${styles.pathCheck} ${done ? styles.pathCheckDone : ''}`}>{done ? '✓' : ''}</span>
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
