import {useEffect, useState} from "react";
import {CircleCheck, CircleOff, KeyRound, Link2, LockKeyhole, Monitor, RefreshCcw, Search, ShieldCheck} from "lucide-react";
import {apiRequest, errorMessage} from "../lib/api";
import type {AffiliateBridgeStatus, AffiliateConnection, DiscoveryProviderStatus} from "../types";
import {Feedback} from "../components/ui/Feedback";

export function SettingsPage() {
  const [account, setAccount] = useState<AffiliateConnection | null>(null);
  const [bridge, setBridge] = useState<AffiliateBridgeStatus | null>(null);
  const [discovery, setDiscovery] = useState<DiscoveryProviderStatus | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function reload() {
    setLoading(true);setError("");
    try {
      const [a,b,d] = await Promise.all([
        apiRequest<AffiliateConnection>("/api/v1/affiliates/mercado-livre/status"),
        apiRequest<AffiliateBridgeStatus>("/api/v1/affiliate-bridge/status"),
        apiRequest<DiscoveryProviderStatus>("/api/v1/discovery/provider-status"),
      ]);
      setAccount(a);setBridge(b);setDiscovery(d);
    }
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
      <p className="mt-3 text-xs text-slate-500">Não há OAuth oficial de afiliados integrado. O conector opcional usa o Chrome no computador do titular.</p>
      <button type="button" className="plain-refresh min-h-11" onClick={()=>void reload()} disabled={loading}><RefreshCcw size={15}/>{loading?"Verificando":"Atualizar status"}</button>
      {error && <Feedback tone="error">{error}</Feedback>}
      <div className="setting-disclaimer">Ainda não existe login OAuth para afiliados implementado neste projeto. Não informe cookies nem senha do Mercado Livre.</div>
    </section>
    <section className="card setting-card min-w-0 px-4 py-6 sm:p-7">
      <div className="setting-top"><span className="setting-provider"><Monitor size={22}/></span>
        <span className={"pill "+(bridge?.worker_online?"pill-good":"pill-neutral")}>
          {bridge?.worker_online?<CircleCheck size={14}/>:<CircleOff size={14}/>}
          {bridge?.worker_online?"Conector online":"Conector offline"}
        </span>
      </div>
      <h2>Gerador de links no computador</h2>
      <p>O Chrome do titular precisa estar aberto com o conector local ativo. É ele quem solicita links pela Central de Afiliados.</p>
      <div className="setting-item flex flex-wrap justify-between gap-2"><span>Conector configurado</span><strong>{bridge?.configured?"Sim":"Não"}</strong></div>
      <div className="setting-item flex flex-wrap justify-between gap-2"><span>Na fila</span><strong>{bridge?.jobs?.PENDING??0}</strong></div>
      <div className="setting-item flex flex-wrap justify-between gap-2"><span>Processando</span><strong>{bridge?.jobs?.PROCESSING??0}</strong></div>
      <div className="setting-item flex flex-wrap justify-between gap-2"><span>Vinculados</span><strong>{bridge?.jobs?.LINKED??0}</strong></div>
      <div className="setting-item flex flex-wrap justify-between gap-2"><span>Falhas</span><strong>{bridge?.jobs?.FAILED??0}</strong></div>
      <small>Online significa comunicação recente com o conector. Não confirma login Mercado Livre nem comissão.</small>
    </section>
    <section className="card setting-card min-w-0 px-4 py-6 sm:p-7">
      <div className="setting-top"><span className="setting-provider"><Search size={22}/></span>
        <span className={"pill "+(discovery?.configured?"pill-good":"pill-neutral")}>
          {discovery?.configured?<CircleCheck size={14}/>:<CircleOff size={14}/>}
          {discovery?.configured?"Configurada":"Não configurada"}
        </span>
      </div>
      <h2>Busca de produtos</h2>
      <p>Fonte: {discovery?.provider==="apify"?"Apify — coleta terceirizada": "Catálogo CSV local"}.</p>
      <small>{discovery?.requires_token&&!discovery?.configured?"Defina APIFY_TOKEN apenas no servidor.": "A configuração não comprova uma consulta ao vivo; execute uma busca de teste para verificar."}</small>
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
