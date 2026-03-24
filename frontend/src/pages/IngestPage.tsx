import IngestView from "../components/ingest/IngestView";
import { useAuth } from "../auth/useAuth";

export default function IngestPage() {
  const { token, clientId } = useAuth();
  return <IngestView token={token} clientId={clientId} />;
}
