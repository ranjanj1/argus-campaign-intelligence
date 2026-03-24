import ChatView from "../components/chat/ChatView";
import { useAuth } from "../auth/useAuth";

interface ChatPageProps {
  onSendQuery: (q: string) => void;
  pendingQuery?: string;
  onPendingQueryConsumed: () => void;
}

export default function ChatPage({ onSendQuery, pendingQuery, onPendingQueryConsumed }: ChatPageProps) {
  const { token, skill, clientId } = useAuth();
  return (
    <ChatView
      token={token}
      skill={skill}
      clientId={clientId}
      onSendQuery={onSendQuery}
      pendingQuery={pendingQuery}
      onPendingQueryConsumed={onPendingQueryConsumed}
    />
  );
}
