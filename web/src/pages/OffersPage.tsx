import {useEffect,useState} from "react";
import {ArrowRight, CheckCircle2, Filter, Inbox, PackageCheck, RefreshCcw} from "lucide-react";
import {apiRequest,errorMessage} from "../lib/api";
import {formatBrl,formatDate} from "../lib/format";
import type {Offer} from "../types";
import {Feedback} from "../components/ui/Feedback";
import {ProductPhoto} from "../components/ui/ProductPhoto";
import {OfferDetails} from "../components/offers/OfferDetails";

type FilterOption="ALL"|"DRAFT"|"APPROVED";

export function OffersPage({adminKey,focusOfferId,onClearFocus}: {
  adminKey:string;focusOfferId:string|null;onClearFocus:()=>void;
}) {
  const [offers,setOffers]=useState<Offer[]>([]);
  const [filter,setFilter]=useState<FilterOption>("ALL");
  const [activeId,setActiveId]=useState<string|null>(focusOfferId);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);
  async function reload(){
    setLoading(true);setError("");
    try {
      const items=await apiRequest<Offer[]>(adminKey,"/api/v1/offers?limit=100");
      setOffers(items);
      setActiveId(current=>current??focusOfferId??items[0]?.id??null);
    }catch(err){setError(errorMessage(err));}
    finally{setLoading(false);}
  }
  useEffect(()=>{void reload();},[adminKey]);
  useEffect(()=>{if(focusOfferId){setActiveId(focusOfferId);onClearFocus();}},[focusOfferId,onClearFocus]);
  const items=offers.filter(x=>filter==="ALL"||x.status===filter);
  const drafts=offers.filter(x=>x.status==="DRAFT").length;
  const approved=offers.filter(x=>x.status==="APPROVED").length;

  return <div className="offers-layout">
    <div className="stats-row">
      <div className="stat-tile"><span className="stat-label">Total de ofertas</span><strong>{offers.length}</strong><span>Produtos cadastrados</span></div>
      <div className="stat-tile"><span className="stat-label">Aguardando revisão</span><strong>{drafts}</strong><span>Rascunhos</span></div>
      <div className="stat-tile"><span className="stat-label">Aprovadas</span><strong>{approved}</strong><span>Prontas para publicação manual</span></div>
    </div>
    <section className="card offers-board">
      <div className="board-heading"><div><span className="eyebrow">PIPELINE</span><h2>Revisão de ofertas</h2><p>Selecione uma oferta para visualizar os detalhes.</p></div><button className="button subtle" onClick={()=>void reload()} disabled={loading}><RefreshCcw size={16}/> Atualizar</button></div>
      {error&&<Feedback tone="error">{error}</Feedback>}
      <div className="filter-pills" role="group" aria-label="Filtrar ofertas"><Filter size={15}/>
        {(["ALL","DRAFT","APPROVED"] as FilterOption[]).map(option=><button type="button" key={option} onClick={()=>setFilter(option)} className={filter===option?"active":""} aria-pressed={filter===option}>{option==="ALL"?"Todas":option==="DRAFT"?"Rascunhos":"Aprovadas"}</button>)}
      </div>
      {loading?<div className="loading-card compact"><div className="spinner"/>Carregando ofertas...</div>:
       items.length===0?<div className="empty-panel"><Inbox size={30}/><h3>Nenhuma oferta nesta etapa</h3><p>Use “Descobrir ofertas” para selecionar produtos para revisão.</p></div>:
       <div className="offer-rows">{items.map(offer=><button type="button" key={offer.id} className={"offer-row "+(activeId===offer.id?"active":"")} onClick={()=>setActiveId(offer.id)}>
         <ProductPhoto url={offer.image_url} title={offer.title}/>
         <span className="offer-row-info"><strong>{offer.title}</strong><small>{formatDate(offer.created_at)}</small><span className="offer-price">{formatBrl(offer.price_cents)}</span></span>
         <span className="offer-row-side"><span className={"pill "+(offer.status==="APPROVED"?"pill-good":"pill-warn")}>{offer.status==="APPROVED"?<CheckCircle2 size={13}/>:<span className="status-dot"/>}{offer.status==="APPROVED"?"Aprovada":"Rascunho"}</span><ArrowRight size={16}/></span>
       </button>)}</div>}
    </section>
    {activeId&&<OfferDetails key={activeId} adminKey={adminKey} offerId={activeId} onUpdated={()=>void reload()}/>}
    {!activeId&&!loading&&<div className="card select-to-review"><PackageCheck size={24}/><p>Selecione uma oferta para revisá-la.</p></div>}
  </div>;
}
