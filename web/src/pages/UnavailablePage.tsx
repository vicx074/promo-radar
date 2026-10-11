import {CalendarClock, Radio, ShieldAlert} from "lucide-react";

export function UnavailablePage({kind}: {kind: "groups" | "campaigns"}) {
  const group = kind === "groups";
  const Icon = group ? Radio : CalendarClock;
  return <section className="card unavailable-card mx-auto w-full max-w-[750px] px-4 py-10 sm:px-10 sm:py-16">
    <div className="unavailable-symbol"><Icon size={29}/></div>
    <span className="eyebrow">EM DESENVOLVIMENTO</span>
    <h2>{group ? "Gerenciamento de grupos vem em breve" : "Agendamento de campanhas vem em breve"}</h2>
    <p>{group
      ? "A Evolution API já possui ferramentas administrativas no backend, mas ainda não existe uma API para gerenciar grupos por este painel."
      : "O backend atual permite apenas publicação manual e explícita. Ainda não existe agendador, limite diário ou envio automático."}</p>
    <div className="unavailable-note"><ShieldAlert size={18}/>
      {group ? "Só serão habilitados destinos autorizados e permitidos pelas regras das plataformas."
        : "Nenhuma publicação será programada ou enviada automaticamente por esta tela."}
    </div>
  </section>;
}
