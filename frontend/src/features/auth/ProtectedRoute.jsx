import React, { useEffect, useState } from "react";
import { Outlet, Navigate, useLocation } from "react-router-dom";
import { me } from "../../api/apiClient";

export default function ProtectedRoute() {
  const [ok, setOk] = useState(null); // null=확인중, true=통과, false=차단
  const location = useLocation();

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await me()
        if (alive) setOk(true); // [G3] 성공 처리
      } catch (e) {
        console.log("인증 실패:", e);
        if (alive) setOk(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  if (ok === null) return <div style={{ padding: 16 }}>인증 중...</div>;
  if (ok) return <Outlet />;
  return <Navigate to="/login" replace state={{ from: location }} />;
}
