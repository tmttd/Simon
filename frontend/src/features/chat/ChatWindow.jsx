import React from "react";

export default function ChatWindow() {
  const onSubmit = (e) => {
    e.preventDefault(); // 전송은 다음 단계에서 연결
  };

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#f6f7fb", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 960, height: "70vh", background: "#fff", borderRadius: 16, boxShadow: "0 10px 30px rgba(0,0,0,0.06)", display: "grid", gridTemplateRows: "auto 1fr auto" }}>
        <header style={{ padding: "16px 20px", borderBottom: "1px solid #eee" }}>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>Simon says</h1>
          <p style={{ margin: "6px 0 0", color: "#6b7280", fontSize: 14 }}>사이먼이 당신의 질문에 응답합니다.</p>
        </header>

        <main style={{ padding: "16px 20px", overflowY: "auto" }}>
          <div style={{ color: "#9ca3af", fontSize: 14 }}>리스트</div>
        </main>

        <form onSubmit={onSubmit} style={{ display: "flex", gap: 8, padding: "12px 12px 16px", borderTop: "1px solid #eee" }}>
          <input
            type="text"
            placeholder="메세지를 입력하세요."
            style={{ flex: 1, padding: "12px 14px", borderRadius: 12, border: "1px solid #e5e7eb", outline: "none" }}
          />
          <button type="submit" style={{ padding: "12px 16px", border: "none", borderRadius: 12, fontWeight: 700, background: "#111827", color: "#fff", cursor: "pointer" }}>
            전송
          </button>
        </form>
      </div>
    </div>
  );
}