import {useEffect, useState, type FormEvent} from "react";
import {ArrowRight, LockKeyhole, Radar, ShieldCheck, Sparkles} from "lucide-react";
import {Sidebar} from "./components/layout/Sidebar";
import {Feedback} from "./components/ui/Feedback";
import {DiscoveryPage} from "./pages/DiscoveryPage";
import {OffersPage} from "./pages/OffersPage";
import {SettingsPage} from "./pages/SettingsPage";
import {HistoryPage} from "./pages/HistoryPage";
import {UnavailablePage} from "./pages/UnavailablePage";
import {errorMessage, loginOwner, logoutOwner, restoreSession} from "./lib/api";
import type {Section} from "./types";

const titles: Record<Section, {kicker: string; title: string; description: string}> = {
  discovery: {kicker: "CATÁLOGO", title: "Descubra novas oportunidades", description: "Encontre produtos por nicho e selecione os que vale a pena compartilhar."},
  offers: {kicker: "CURADORIA", title: "Suas ofertas, sob controle", description: "Cadastre o link de afiliado, revise e aprove cada publicação."},
  groups: {kicker: "CANAIS", title: "Grupos WhatsApp", description: "Conexões e permissões dos destinos de publicação."},
  campaigns: {kicker: "AUTOMAÇÃO", title: "Programações", description: "Organize a frequência de envio das ofertas."},
  history: {kicker: "RASTREABILIDADE", title: "Histórico de envios", description: "Consulte o resultado das publicações pelo identificador."},
  settings: {kicker: "INTEGRAÇÕES", title: "Configurações", description: "Confira o estado das suas conexões e a proteção das credenciais."},
};

export function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [section, setSection] = useState<Section>("discovery");
  const [focusOfferId, setFocusOfferId] = useState<string | null>(null);
  const [loginError, setLoginError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let mounted = true;
    void restoreSession()
      .then(() => {if (mounted) setAuthenticated(true);})
      .catch(() => {if (mounted) setAuthenticated(false);});
    const handleExpired = () => setAuthenticated(false);
    window.addEventListener("promo:session-expired", handleExpired);
    return () => {mounted = false; window.removeEventListener("promo:session-expired", handleExpired);};
  }, []);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!password) return;
    setSubmitting(true);
    setLoginError("");
    try {
      await loginOwner(password);
      setPassword("");
      setAuthenticated(true);
    } catch (error) {
      setLoginError(errorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  async function logout() {
    try {
      await logoutOwner();
    } catch {
      window.alert("Não foi possível invalidar a sessão no servidor. Tente sair novamente.");
      return;
    }
    setAuthenticated(false);
    setPassword("");
    setFocusOfferId(null);
    setSection("discovery");
  }

  if (authenticated === null) return (
    <main className="login-page"><div className="loading-card">
      <div className="spinner"/> Verificando acesso ao seu painel...
    </div></main>
  );

  if (!authenticated) return (
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
          <p>Informe sua senha privada para entrar no Promo Radar.</p>
          <label htmlFor="admin-key">Senha do painel</label>
          <input id="admin-key" type="password" value={password} onChange={e=>setPassword(e.target.value)}
            placeholder="Digite sua senha" autoComplete="current-password" spellCheck={false} required />
          <button type="submit" className="button primary full" disabled={submitting || !password}>
            {submitting ? "Verificando..." : "Entrar no painel"} <ArrowRight size={17}/>
          </button>
          {loginError && <Feedback tone="error">{loginError}</Feedback>}
          <div className="login-privacy"><ShieldCheck size={16}/> Sua senha não é armazenada no navegador. Sua sessão pode ser encerrada a qualquer momento.</div>
          <div className="login-notice">Este acesso é ao Promo Radar, não à sua conta Mercado Livre.</div>
        </form>
      </div>
    </main>
  );

  const current = titles[section];
  return <div className="app-shell">
    <Sidebar section={section} onNavigate={setSection} onLogout={()=>{void logout();}}/>
    <div className="main-region">
      <header className="topbar">
        <div className="topbar-path">Meu painel <span>/</span> <strong>{current.title}</strong></div>
        <div className="topbar-profile"><span className="profile-dot" /> Acesso privado <span className="avatar">PR</span></div>
      </header>
      <main className="workspace">
        <div className="page-heading">
          <div><div className="eyebrow">{current.kicker}</div><h1>{current.title}</h1><p>{current.description}</p></div>
          <span className="page-heading-icon"><Sparkles size={23} /></span>
        </div>
        {section === "discovery" && <DiscoveryPage onOpenOffer={id=>{setFocusOfferId(id);setSection("offers");}} />}
        {section === "offers" && <OffersPage focusOfferId={focusOfferId} onClearFocus={()=>setFocusOfferId(null)} />}
        {section === "settings" && <SettingsPage />}
        {section === "history" && <HistoryPage />}
        {section === "groups" && <UnavailablePage kind="groups" />}
        {section === "campaigns" && <UnavailablePage kind="campaigns" />}
      </main>
    </div>
  </div>;
}
