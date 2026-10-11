import {useEffect, useState} from "react";
import {CircleCheck, CircleOff, KeyRound, Link2, LockKeyhole, RefreshCcw, ShieldCheck} from "lucide-react";
import {apiRequest, errorMessage} from "../lib/api";
import type {AffiliateConnection} from "../types";
import {Feedback} from "../components/ui/Feedback";

export function SettingsPage() {
  const [account, setAccount] = useState<AffiliateConnection | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function reload() {
    setLoading(true);setError("");
    try {setAccount(await apiRequest<AffiliateConnection>( "/api/v1/affiliates/mercado-livre/status"));}
    catch (err) {setError(errorMessage(err));}
    finally {setLoading(false);}
  }
  useEffect(() => {void reload();}, []);
  return <div className="settings-grid grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-2 xl:gap-5">
    <section className="card setting-card min-w-0 px-4 py-6 sm:p-7">
      <div className="setting-top"><span className="setting-provider"><Link2 size={22}/></span>
        <span className={"pill "+(account?.connected?"pill-good":"pill-neutral")}>
          {account?.connected?<CircleCheck size={14}/>:<CircleOff size={14}/>}
          {account?.connected?"Conectado":"Não conectado"}
        </span>
      </div>
      <h2>Mercado Livre</h2>
      <p>Integração com a conta do Programa de Afiliados.</p>
      <div className="setting-item flex flex-wrap items-center justify-between gap-2"><span>Geração automática de links</span><strong>{account?.auto_generation_available?"Disponível":"Indisponível"}</strong></div>
      <div className="setting-item"><span>Método de conexão</span><strong>{account?.connected?"Autorizado":"Ainda não configurado"}</strong></div>
      <button type="button" disabled className="button muted full"><LockKeyhole size={17}/> Conexão de afiliados em análise</button>
      <button type="button" className="plain-refresh min-h-11" onClick={()=>void reload()} disabled={loading}><RefreshCcw size={15}/>{loading?"Verificando":"Atualizar status"}</button>
      {error && <Feedback tone="error">{error}</Feedback>}
      <div className="setting-disclaimer">Ainda não existe login OAuth para afiliados implementado neste projeto. Não informe cookies nem senha do Mercado Livre.</div>
    </section>
    <section className="card setting-card security-card min-w-0 px-4 py-6 sm:p-7">
      <div className="setting-top"><span className="setting-provider"><KeyRound size={22}/></span><span className="pill pill-good"><CircleCheck size={14}/> Ativo</span></div>
      <h2>Acesso administrativo</h2>
      <p>O painel é protegido por uma senha única e sessão segura no servidor.</p>
      <div className="security-reminder"><ShieldCheck size={21}/><span><strong>Senha protegida por Argon2id</strong><small>O navegador recebe um cookie HttpOnly, sem acesso à senha ou à chave administrativa.</small></span></div>
      <div className="security-reminder"><LockKeyhole size={21}/><span><strong>Envio bloqueado por padrão</strong><small>O backend exige aprovação explícita e SEND_ENABLED=true antes de publicar.</small></span></div>
    </section>
  </div>;
}
