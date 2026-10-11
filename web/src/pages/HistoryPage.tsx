import {useState, type FormEvent} from "react";
import {ArrowRight, FileClock, Search} from "lucide-react";
import {apiRequest, errorMessage} from "../lib/api";
import {formatDate} from "../lib/format";
import type {Publication} from "../types";
import {Feedback} from "../components/ui/Feedback";

export function HistoryPage({adminKey}: {adminKey: string}) {
  const [id, setId] = useState("");
  const [record, setRecord] = useState<Publication | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function lookup(event: FormEvent) {
    event.preventDefault();
    const code = id.trim();
    if (!/^[0-9a-f-]{36}$/i.test(code)) { setError("Informe um UUID de publicação válido."); return; }
    setBusy(true);setError("");setRecord(null);
    try {
      setRecord(await apiRequest<Publication>(adminKey, "/api/v1/publications/" + encodeURIComponent(code)));
    } catch(err) {setError(errorMessage(err));}
    finally {setBusy(false);}
  }
  return <div className="history-layout">
    <div className="card history-lookup">
      <span className="section-icon"><FileClock size={21}/></span>
      <h2>Consultar publicação</h2>
      <p>Informe o ID recebido após uma publicação para consultar seu estado. A listagem completa ainda não está disponível na API.</p>
      <form onSubmit={lookup} className="search-field history-search">
        <Search size={18} /><input aria-label="ID da publicação" value={id} onChange={e=>setId(e.target.value)}
          placeholder="Cole aqui o ID da publicação" spellCheck={false} />
        <button className="button primary" type="submit" disabled={busy || !id.trim()}>{busy?"Consultando":"Consultar"}<ArrowRight size={16}/></button>
      </form>
      {error && <Feedback tone="error">{error}</Feedback>}
      {record && <div className="history-result">
        <div className="result-title"><strong>Status</strong><span className={"pill "+(record.status==="SENT"?"pill-good":"pill-warn")}>{record.status}</span></div>
        <dl><div><dt>Publicação</dt><dd>{record.id}</dd></div>
          <div><dt>Oferta</dt><dd>{record.offer_id}</dd></div>
          <div><dt>Criada em</dt><dd>{formatDate(record.created_at)}</dd></div>
          <div><dt>Última atualização</dt><dd>{formatDate(record.updated_at)}</dd></div></dl>
        <Feedback tone="info">{record.status === "SENT"
          ? "SENT confirma aceite HTTP da Evolution, não a entrega no grupo."
          : "SENDING/UNKNOWN exigem conferência manual antes de qualquer nova tentativa."}</Feedback>
      </div>}
    </div>
  </div>;
}
