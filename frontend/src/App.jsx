import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Link } from "react-router-dom";
import LoginForm from "./features/auth/LoginForm";
import SignupForm from "./features/auth/SignupForm";
import ChatPage from "./features/chat/ChatPage"; // ChatWindow 대신 ChatPage를 임포트
import Start from "./features/chat/Start";
import GroupsDashboard from "./features/chat/GroupsDashboard";
import ExamPage from "./features/chat/ExamPage";
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
            <Route path="/start" element={<Start />} />
            <Route path="/dashboard" element={<GroupsDashboard />} />
            <Route path="/exam/:sessionId" element={<ExamPage />} />
            <Route path="/session/:groupId/chat" element={<ChatPage />} />
            <Route path="/session/:groupId/chat/:threadId" element={<ChatPage />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
