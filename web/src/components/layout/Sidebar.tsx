import {
  ChevronLeft, CircleHelp, History, LayoutGrid, LifeBuoy,
  PackageCheck, Settings2, ShieldCheck, Sparkles,
} from "lucide-react";
import type {Section} from "../../types";
import {LetterSwap} from "../ui/LetterSwap";

export const navigation: Array<{id: Section; label: string; icon: typeof LayoutGrid}> = [
  {id: "discovery", label: "Descobrir", icon: LayoutGrid},
  {id: "offers", label: "Ofertas", icon: PackageCheck},
  {id: "history", label: "Histórico", icon: History},
  {id: "settings", label: "Ajustes", icon: Settings2},
];

export function Sidebar({section, onNavigate, onLogout}: {
  section: Section;
  onNavigate: (value: Section) => void;
  onLogout: () => void;
}) {
  return <>
    <aside className="sidebar hidden w-[205px] shrink-0 md:flex xl:w-[250px]">
      <div className="sidebar-brand">
        <span className="brand-symbol"><Sparkles size={20} strokeWidth={2.4} /></span>
        <span><strong><LetterSwap text="promo radar" /></strong><small>central de ofertas</small></span>
      </div>
      <div className="sidebar-scroll">
        <div className="nav-heading">PAINEL</div>
        <nav aria-label="Navegação principal" className="nav-list">
          {navigation.map(page => <button
            key={page.id} type="button"
            className={"nav-button min-h-11 " + (section === page.id ? "active" : "")}
            aria-current={section === page.id ? "page" : undefined}
            onClick={() => onNavigate(page.id)}
          ><page.icon size={19} strokeWidth={1.9} /><span>{page.label}</span>
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
        <span className="side-version"><CircleHelp size={13} /> Painel privado · v0.1</span>
      </footer>
    </aside>

    {/* Navegação de polegar: disponível também em celulares pequenos. */}
    <nav
      aria-label="Navegação inferior"
      className="fixed inset-x-0 bottom-0 z-50 grid grid-cols-4 border-t border-slate-200 bg-white/95 px-2 pt-1 pb-[max(0.5rem,env(safe-area-inset-bottom))] shadow-[0_-10px_30px_rgba(26,68,114,0.08)] backdrop-blur-lg md:hidden"
    >
      {navigation.map(page => {
        const Icon = page.icon;
        const active = section === page.id;
        return <button
          key={page.id}
          type="button"
          aria-current={active ? "page" : undefined}
          aria-label={page.label}
          onClick={() => onNavigate(page.id)}
          className={"flex min-h-[54px] min-w-0 flex-col items-center justify-center gap-1 rounded-xl px-1 text-[11px] font-bold transition-colors " +
            (active ? "bg-blue-50 text-blue-700" : "text-slate-500 hover:bg-slate-50 active:bg-slate-100")}
        >
          <Icon size={21} strokeWidth={active ? 2.5 : 1.9} aria-hidden="true"/>
          <span className="truncate">{page.label}</span>
        </button>;
      })}
    </nav>
  </>;
}
