import {
  ChevronLeft, CircleHelp, History, LayoutGrid, LifeBuoy,
  PackageCheck, Settings2, ShieldCheck, Sparkles,
} from "lucide-react";
import type {Section} from "../../types";
import {LetterSwap} from "../ui/LetterSwap";

const pages: Array<{id: Section; label: string; icon: typeof LayoutGrid; soon?: boolean}> = [
  {id: "discovery", label: "Descobrir", icon: LayoutGrid},
  {id: "offers", label: "Ofertas", icon: PackageCheck},
  {id: "history", label: "Histórico", icon: History},
  {id: "settings", label: "Configurações", icon: Settings2},
];

export function Sidebar({section, onNavigate, onLogout}: {
  section: Section;
  onNavigate: (value: Section) => void;
  onLogout: () => void;
}) {
  return <aside className="sidebar">
    <div className="sidebar-brand">
      <span className="brand-symbol"><Sparkles size={20} strokeWidth={2.4} /></span>
      <span><strong><LetterSwap text="promo radar" /></strong><small>central de ofertas</small></span>
    </div>
    <div className="sidebar-scroll">
      <div className="nav-heading">PAINEL</div>
      <nav aria-label="Navegação principal" className="nav-list">
        {pages.map(page => <button
          key={page.id} type="button"
          className={"nav-button " + (section === page.id ? "active" : "")}
          aria-current={section === page.id ? "page" : undefined}
          onClick={() => onNavigate(page.id)}
        ><page.icon size={19} strokeWidth={1.9} /><span>{page.label}</span>
          {page.soon && <span className="nav-soon">Em breve</span>}
        </button>)}
      </nav>
      <div className="sidebar-helper">
        <span className="helper-icon"><ShieldCheck size={21} /></span>
        <strong>Curadoria com controle</strong>
        <p>Ofertas revisadas antes de qualquer envio.</p>
        <span className="helper-status"><span className="status-dot" /> Proteção de envio ativa</span>
      </div>
    </div>
    <footer className="sidebar-footer">
      <a href="https://github.com/vicx074/promo-radar" rel="noreferrer" target="_blank"><LifeBuoy size={16} /> Documentação</a>
      <button type="button" onClick={onLogout}><ChevronLeft size={16} /> Sair</button>
      <span className="side-version"><CircleHelp size={13} /> Painel MVP · v0.1</span>
    </footer>
  </aside>;
}
