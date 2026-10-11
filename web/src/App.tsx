import {useState, type FormEvent} from "react";
import {ArrowRight, LockKeyhole, Radar, ShieldCheck, Sparkles} from "lucide-react";
import {Sidebar} from "./components/layout/Sidebar";
import {Feedback} from "./components/ui/Feedback";
import {DiscoveryPage} from "./pages/DiscoveryPage";
import {OffersPage} from "./pages/OffersPage";
import {SettingsPage} from "./pages/SettingsPage";
import {HistoryPage} from "./pages/HistoryPage";
import {UnavailablePage} from "./pages/UnavailablePage";
import {apiRequest, errorMessage} from "./lib/api";
import type {AffiliateConnection, Section} from "./types";

const titles: Record<Section, {kicker: string; title: string; description: string}> = {
  discovery: {kicker: "CATÁLOGO", title: "Descubra novas oportunidades", description: "Encontre produtos por nicho e selecione os que vale a pena compartilhar."},
  offers: {kicker: "CURADORIA", title: "Suas ofertas, sob controle", description: "Cadastre o link de afiliado, revise e aprove cada publicação."},
  groups: {kicker: "CANAIS", title: "Grupos WhatsApp", description: "Conexões e permissões dos destinos de publicação."},
  campaigns: {kicker: "AUTOMAÇÃO", title: "Programações", description: "Organize a frequência de envio das ofertas."},
  history: {kicker: "RASTREABILIDADE", title: "Histórico de envios", description: "Consulte o resultado das publicações pelo identificador."},
  settings: {kicker: "INTEGRAÇÕES", title: "Configurações", description: "Confira o estado das suas conexões e a proteção das credenciais."},
};

export function App() {
  const [adminKey, setAdminKey] = useState("");
  const [keyDraft, setKeyDraft] = useState("");
  const [section, setSection] = useState<Section>("discovery");
  const [focusOfferId, setFocusOfferId] = useState<string | null>(null);
  const [loginError, setLoginError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!keyDraft.trim()) return;
    setSubmitting(true);
    setLoginError("");
    try {
      await apiRequest<AffiliateConnection>(keyDraft, "/api/v1/affiliates/mercado-livre/status");
      setAdminKey(keyDraft);
      setKeyDraft("");
    } catch (error) {
      setLoginError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  function logout() {
    setAdminKey("");
    setKeyDraft("");
    setFocusOfferId(null);
    setSection("discovery");
  }

  if (!adminKey) return (
    <main className="login-page">
      <div className="login-decor login-decor-one" /><div className="login-decor login-decor-two" />
      <div className="login-container">
        <div className="login-intro">
          <span className="login-brand"><Sparkles size={22} /> promo radar <span>· painel</span></span>
          <div className="eyebrow light">ORGANIZE. REVISE. COMPARTILHE.</div>
          <h1>Boas ofertas merecem <span>um olhar especial.</span></h1>
          <p>O seu espaço para encontrar produtos, preparar promoções e controlar o que será divulgado.</p>
          <div className="login-highlights"><span><ShieldCheck size={17}/> Aprovação humana</span><span><Radar size={17}/> Busca sob demanda</span></div>
        </div>
        <form className="login-form card" onSubmit={handleLogin}>
          <div className="login-icon"><LockKeyhole size={24}/></div>
          <h2>Acesse seu painel</h2>
          <p>Informe a chave administrativa configurada no backend para continuar.</p>
          <label htmlFor="admin-key">Chave administrativa</label>
          <input id="admin-key" type="password" value={keyDraft} onChange={e=>setKeyDraft(e.target.value)}
            placeholder="Sua ADMIN_API_KEY" autoComplete="off" spellCheck={false} required />
          <button type="submit" className="button primary full" disabled={submitting || !keyDraft.trim()}>
            {submitting ? "Verificando..." : "Entrar no painel"} <ArrowRight size={17}/>
          </button>
          {loginError && <Feedback tone="error">{loginError}</Feedback>}
          <div className="login-privacy"><ShieldCheck size={16}/> A chave permanece somente na memória desta aba; não é salva no navegador.</div>
          <div className="login-notice">Este acesso é ao Promo Radar, não à sua conta Mercado Livre.</div>
        </form>
      </div>
    </main>
  );

  const current = titles[section];
  return <div className="app-shell">
    <Sidebar section={section} onNavigate={setSection} onLogout={logout}/>
    <div className="main-region">
      <header className="topbar">
        <div className="topbar-path">Workspace <span>/</span> <strong>{current.title}</strong></div>
        <div className="topbar-profile"><span className="profile-dot" /> Acesso administrativo <span className="avatar">PR</span></div>
      </header>
      <main className="workspace">
        <div className="page-heading">
          <div><div className="eyebrow">{current.kicker}</div><h1>{current.title}</h1><p>{current.description}</p></div>
          <span className="page-heading-icon"><Sparkles size={23} /></span>
        </div>
        {section === "discovery" && <DiscoveryPage adminKey={adminKey} onOpenOffer={id=>{setFocusOfferId(id);setSection("offers");}} />}
        {section === "offers" && <OffersPage adminKey={adminKey} focusOfferId={focusOfferId} onClearFocus={()=>setFocusOfferId(null)} />}
        {section === "settings" && <SettingsPage adminKey={adminKey} />}
        {section === "history" && <HistoryPage adminKey={adminKey} />}
        {section === "groups" && <UnavailablePage kind="groups" />}
        {section === "campaigns" && <UnavailablePage kind="campaigns" />}
      </main>
    </div>
  </div>;
}
