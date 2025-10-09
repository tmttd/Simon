import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import LoginForm from "./features/auth/LoginForm";
import SignupForm from "./features/auth/SignupForm";
import ChatPage from "./features/chat/ChatPage"; // ChatWindow 대신 ChatPage를 임포트
import InitStudy from "./features/chat/InitStudy";
import GroupsDashboard from "./features/chat/GroupsDashboard";
import ProtectedRoute from "./routes/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
          <Route path="/signup" element={<SignupForm />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/init-study" element={<InitStudy />} />
            <Route path="/dashboard" element={<GroupsDashboard />} />
            <Route path="/group/:groupId/chat" element={<ChatPage />} />
            <Route path="/group/:groupId/chat/:threadId" element={<ChatPage />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
