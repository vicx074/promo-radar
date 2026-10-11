import {useEffect, useState, type FormEvent} from "react";
import {ArrowRight, LockKeyhole, LogOut, Radar, ShieldCheck, Sparkles} from "lucide-react";
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
    <main className="login-page grid min-h-dvh place-items-center p-4 sm:p-8"><div className="loading-card">
      <div className="spinner"/> Verificando acesso ao seu painel...
    </div></main>
  );

  if (!authenticated) return (
    <main className="login-page grid min-h-dvh place-items-center p-4 sm:p-8">
      <div className="login-decor login-decor-one" /><div className="login-decor login-decor-two" />
      <div className="login-container grid w-full max-w-[1050px] grid-cols-1 items-center gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
        <div className="login-intro min-w-0">
          <span className="login-brand mb-5 sm:mb-9 lg:mb-14"><Sparkles size={22} /> promo radar <span>· painel</span></span>
          <div className="eyebrow light hidden sm:block">ORGANIZE. REVISE. COMPARTILHE.</div>
          <h1 className="hidden text-[30px] sm:block sm:text-[35px] lg:text-[43px]">Boas ofertas merecem <span>um olhar especial.</span></h1>
          <p className="hidden sm:block">O seu espaço para encontrar produtos, preparar promoções e controlar o que será divulgado.</p>
          <div className="login-highlights hidden sm:flex"><span><ShieldCheck size={17}/> Aprovação humana</span><span><Radar size={17}/> Busca sob demanda</span></div>
        </div>
        <form className="login-form card w-full min-w-0 px-5 py-7 sm:p-9" onSubmit={handleLogin}>
          <div className="login-icon"><LockKeyhole size={24}/></div>
          <h2>Acesse seu painel</h2>
          <p>Informe sua senha privada para entrar no Promo Radar.</p>
          <label htmlFor="admin-key">Senha do painel</label>
          <input id="admin-key" type="password" value={password} onChange={e=>setPassword(e.target.value)}
            placeholder="Digite sua senha" autoComplete="current-password" className="min-h-12 text-base sm:text-sm" spellCheck={false} required />
          <button type="submit" className="button primary full min-h-12 text-sm" disabled={submitting || !password}>
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
  return <div className="app-shell block min-h-dvh md:flex">
    <Sidebar section={section} onNavigate={setSection} onLogout={()=>{void logout();}}/>
    <div className="main-region min-w-0 flex-1">
      <header className="topbar flex h-[60px] items-center justify-between gap-3 px-4 sm:px-6 md:h-[77px] xl:px-11">
        <div className="topbar-path hidden md:block">Meu painel <span>/</span> <strong>{current.title}</strong></div>
        <div className="topbar-profile hidden md:flex"><span className="profile-dot" /> Acesso privado <span className="avatar">PR</span></div>
        <div className="flex items-center gap-2 md:hidden"><span className="brand-symbol !h-9 !w-9"><Sparkles size={18}/></span><strong className="text-sm font-extrabold tracking-tight text-blue-800">promo radar</strong></div>
        <button type="button" aria-label="Sair do painel" title="Sair do painel" onClick={()=>{void logout();}} className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-xl border border-slate-200 text-slate-600 active:bg-slate-100 md:hidden"><LogOut size={19}/></button>
      </header>
      <main className="workspace mx-auto max-w-[1660px] min-w-0 px-4 pt-6 pb-[calc(7rem+env(safe-area-inset-bottom))] sm:px-6 md:py-9 xl:px-11">
        <div className="page-heading mb-6 flex items-start justify-between gap-3 md:mb-8">
          <div className="min-w-0"><div className="eyebrow">{current.kicker}</div><h1 className="text-[22px] leading-tight sm:text-[26px]">{current.title}</h1><p className="max-w-[680px] text-xs leading-relaxed">{current.description}</p></div>
          <span className="page-heading-icon hidden shrink-0 md:grid"><Sparkles size={23} /></span>
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
