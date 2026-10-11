import {useEffect,useRef,useState} from "react";
import {ArrowRight, CheckCircle2, Filter, Inbox, PackageCheck, RefreshCcw} from "lucide-react";
import {apiRequest,errorMessage} from "../lib/api";
import {formatBrl,formatDate} from "../lib/format";
import type {Offer} from "../types";
import {Feedback} from "../components/ui/Feedback";
import {ProductPhoto} from "../components/ui/ProductPhoto";
import {OfferDetails} from "../components/offers/OfferDetails";

type FilterOption="ALL"|"DRAFT"|"APPROVED";

export function OffersPage({focusOfferId,onClearFocus}: {
  focusOfferId:string|null;onClearFocus:()=>void;
}) {
  const [offers,setOffers]=useState<Offer[]>([]);
  const detailRef=useRef<HTMLDivElement>(null);
  const listRef=useRef<HTMLElement>(null);
  const shouldScrollToDetail=useRef(Boolean(focusOfferId));
  const [filter,setFilter]=useState<FilterOption>("ALL");
  const [activeId,setActiveId]=useState<string|null>(focusOfferId);
  const [error,setError]=useState("");
  const [loading,setLoading]=useState(true);
  async function reload(){
    setLoading(true);setError("");
    try {
      const items=await apiRequest<Offer[]>("/api/v1/offers?limit=100");
      setOffers(items);
      setActiveId(current=>current??focusOfferId??items[0]?.id??null);
    }catch(err){setError(errorMessage(err));}
    finally{setLoading(false);}
  }
  useEffect(()=>{void reload();},[]);
  useEffect(()=>{
    if(focusOfferId){
      shouldScrollToDetail.current=true;
      setActiveId(focusOfferId);
      onClearFocus();
    }
  },[focusOfferId,onClearFocus]);
  useEffect(()=>{
    if(!activeId||!shouldScrollToDetail.current)return;
    shouldScrollToDetail.current=false;
    if(window.matchMedia("(max-width: 1279px)").matches){
      requestAnimationFrame(()=>detailRef.current?.scrollIntoView({block:"start",behavior:"smooth"}));
    }
  },[activeId]);
  function selectOffer(id:string){
    shouldScrollToDetail.current=true;
    setActiveId(id);
    if(activeId===id&&window.matchMedia("(max-width: 1279px)").matches){
      detailRef.current?.scrollIntoView({block:"start",behavior:"smooth"});
    }
  }
  const items=offers.filter(x=>filter==="ALL"||x.status===filter);
  const drafts=offers.filter(x=>x.status==="DRAFT").length;
  const approved=offers.filter(x=>x.status==="APPROVED").length;

  return <div className="offers-layout grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)] xl:gap-5">
    <div className="stats-row col-span-full grid grid-cols-2 gap-2 sm:grid-cols-3 sm:gap-4">
      <div className="stat-tile"><span className="stat-label">Total de ofertas</span><strong>{offers.length}</strong><span>Produtos cadastrados</span></div>
      <div className="stat-tile"><span className="stat-label">Aguardando revisão</span><strong>{drafts}</strong><span>Rascunhos</span></div>
      <div className="stat-tile col-span-2 sm:col-span-1"><span className="stat-label">Aprovadas</span><strong>{approved}</strong><span>Prontas para publicação manual</span></div>
    </div>
    <section ref={listRef} className="card offers-board min-w-0 scroll-mt-4 p-4 sm:p-6">
      <div className="board-heading flex flex-wrap items-start justify-between gap-3"><div><span className="eyebrow">PIPELINE</span><h2>Revisão de ofertas</h2><p>Selecione uma oferta para visualizar os detalhes.</p></div><button className="button subtle min-h-11" onClick={()=>void reload()} disabled={loading}><RefreshCcw size={16}/> Atualizar</button></div>
      {error&&<Feedback tone="error">{error}</Feedback>}
      <div className="filter-pills flex flex-wrap items-center gap-2" role="group" aria-label="Filtrar ofertas"><Filter size={15}/>
        {(["ALL","DRAFT","APPROVED"] as FilterOption[]).map(option=><button type="button" key={option} onClick={()=>setFilter(option)} className={filter===option?"active":""} aria-pressed={filter===option}>{option==="ALL"?"Todas":option==="DRAFT"?"Rascunhos":"Aprovadas"}</button>)}
      </div>
      {loading?<div className="loading-card compact"><div className="spinner"/>Carregando ofertas...</div>:
       items.length===0?<div className="empty-panel"><Inbox size={30}/><h3>Nenhuma oferta nesta etapa</h3><p>Use “Descobrir ofertas” para selecionar produtos para revisão.</p></div>:
       <div className="offer-rows">{items.map(offer=><button type="button" key={offer.id} className={"offer-row min-h-[84px] min-w-0 touch-manipulation "+(activeId===offer.id?"active":"")} onClick={()=>selectOffer(offer.id)}>
         <ProductPhoto url={offer.image_url} title={offer.title}/>
         <span className="offer-row-info min-w-0"><strong>{offer.title}</strong><small>{formatDate(offer.created_at)}</small><span className="offer-price">{formatBrl(offer.price_cents)}</span></span>
         <span className="offer-row-side shrink-0"><span className={"pill "+(offer.status==="APPROVED"?"pill-good":"pill-warn")}>{offer.status==="APPROVED"?<CheckCircle2 size={13}/>:<span className="status-dot"/>}{offer.status==="APPROVED"?"Aprovada":"Rascunho"}</span><ArrowRight size={16}/></span>
       </button>)}</div>}
    </section>
    {activeId&&<div ref={detailRef} className="min-w-0 scroll-mt-5 xl:sticky xl:top-5"><button type="button" className="mb-3 inline-flex min-h-11 items-center rounded-lg px-2 text-xs font-bold text-blue-700 xl:hidden" onClick={()=>listRef.current?.scrollIntoView({block:"start",behavior:"smooth"})}>← Voltar à lista</button><OfferDetails key={activeId} offerId={activeId} onUpdated={()=>void reload()}/></div>}
    {!activeId&&!loading&&<div className="card select-to-review"><PackageCheck size={24}/><p>Selecione uma oferta para revisá-la.</p></div>}
  </div>;
}
