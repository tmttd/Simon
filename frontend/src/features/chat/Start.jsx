import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { classifyStudy } from "../../api/apiClient";
import styles from "./Start.module.css";

export default function Start() {
  const navigate = useNavigate();
  const [noteText, setNoteText] = useState("");
  const [files, setFiles] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  const handleFileChange = (e) => {
    const list = Array.from(e.target.files || []);
    setFiles((prev) => {
      const combined = [...prev, ...list];
      const seen = new Set();
      const unique = [];
      for (const f of combined) {
        const key = `${f.name}-${f.size}-${f.lastModified}`;
        if (!seen.has(key)) {
          seen.add(key);
          unique.push(f);
        }
      }
      return unique;
    });
    if (e.target) e.target.value = "";
  };

  const removeFileAt = (idx) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const data = await classifyStudy({ noteText, files });
      navigate('/dashboard', { state: { highlightGroupId: data?.group?.id || null } });
    } catch (e) {
      setError(e?.response?.data?.error || "요청 처리 중 오류가 발생했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (!isSubmitting) return;
    const start = Date.now();
    setElapsed(0);
    const id = setInterval(() => {
      setElapsed(((Date.now() - start) / 1000));
    }, 100);
    return () => clearInterval(id);
  }, [isSubmitting]);

  return (
    <div className={styles.page}>
      <div className={`${styles.board} ${isSubmitting ? styles.blurred : ""}`}>
        <div className={styles.header}>학습 세션 생성</div>
        <div className={styles.navRow}>
          <button type="button" className={`${styles.sideCta} ${styles.sideCtaPrimary}`} onClick={() => navigate('/dashboard')}>
            ← 대시보드로
          </button>

          <div className={styles.formWrap}>
            <form id="initStudyForm" onSubmit={handleSubmit} className={styles.form}>
              <label className={styles.label}>메모 입력</label>
              <textarea
                value={noteText}
                onChange={(e) => setNoteText(e.target.value)}
                placeholder="여기에 메모/핵심 내용을 자유롭게 입력하세요"
                className={styles.textarea}
              />

              <label className={styles.label}>이미지 업로드</label>
              <div className={styles.uploader}>
                <input
                  id="files"
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleFileChange}
                />
                <label htmlFor="files" className={styles.uploadBtn}>이미지 선택</label>
                <div className={styles.fileList}>
                  {files.map((f, idx) => (
                    <span key={`${f.name}-${f.size}-${f.lastModified}-${idx}`} className={styles.fileBadge}>
                      {f.name}
                      <button type="button" className={styles.fileBadgeBtn} onClick={() => removeFileAt(idx)} aria-label="remove file">×</button>
                    </span>
                  ))}
                </div>
              </div>

              {error && <div className={styles.error}>{error}</div>}
            </form>
          </div>

          <button type="submit" form="initStudyForm" className={`${styles.sideCta} ${styles.sideCtaPrimary}`} disabled={isSubmitting}>
            분석 및 학습하기 →
          </button>
        </div>
      </div>

      {isSubmitting && (
        <div className={styles.overlay}>
          <div className={styles.overlayCard}>
            <div className={styles.spinner} aria-hidden="true" />
            <div className={styles.overlayTitle}>사이먼 AI가 학습 세션을 생성하고 있습니다.</div>
            <div className={styles.overlayDesc}>잠시 기다려주세요.</div>
            <div className={styles.overlayTimer}>{elapsed.toFixed(1)}s</div>
          </div>
        </div>
      )}
    </div>
  );
}


