import { Navigate, Route, Routes } from "react-router-dom";
import { useState } from "react";
import Sidebar from "./components/layout/Sidebar";
import ChatPage from "./pages/ChatPage";
import IngestPage from "./pages/IngestPage";
import CollectionsPage from "./pages/CollectionsPage";
import FeedbackPage from "./pages/FeedbackPage";
import LoginPage from "./pages/LoginPage";
import { useAuth } from "./auth/useAuth";
import { useQueryHistory } from "./hooks/useQueryHistory";
import { useNavigate } from "react-router-dom";
import { BG } from "./design/tokens";

function AppShell() {
  const { token, skill, clientId, setSkill, setClientId, devMode, clearToken } = useAuth();

  if (!devMode && !token) return <LoginPage />;
  const { history, push, remove } = useQueryHistory();
  const navigate = useNavigate();
  const [chatKey, setChatKey] = useState(0);
  const [pendingQuery, setPendingQuery] = useState<string | undefined>();

  const handleHistoryClick = (q: string) => {
    navigate("/chat");
    setPendingQuery(q);
  };

  const handleNewChat = () => {
    sessionStorage.removeItem("argus_session_id");
    navigate("/chat");
    setChatKey((k) => k + 1);
    setPendingQuery(undefined);
  };

  const handleSendQuery = (q: string) => {
    push(q);
  };

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        background: BG,
        overflow: "hidden",
      }}
    >
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <Sidebar
          activeSkill={skill}
          setSkill={setSkill}
          activeClient={clientId}
          setClient={setClientId}
          history={history}
          onHistoryClick={handleHistoryClick}
          onHistoryDelete={remove}
          onNewChat={handleNewChat}
          onLogout={!devMode ? clearToken : undefined}
          devMode={devMode}
        />
        <div style={{ flex: 1, display: "flex", overflow: "hidden", background: BG }}>
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route
              path="/chat"
              element={
                <ChatPage
                  key={chatKey}
                  onSendQuery={handleSendQuery}
                  pendingQuery={pendingQuery}
                  onPendingQueryConsumed={() => setPendingQuery(undefined)}
                />
              }
            />
            <Route path="/ingest" element={<IngestPage />} />
            <Route path="/collections" element={<CollectionsPage />} />
            <Route path="/feedback" element={<FeedbackPage />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return <AppShell />;
}
