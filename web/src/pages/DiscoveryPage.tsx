import {useState, type FormEvent} from "react";
import {ArrowRight, Check, CheckCheck, Clock3, MousePointer2, PackageSearch, Search, Sparkles} from "lucide-react";
import {apiRequest, errorMessage} from "../lib/api";
import {formatBrl} from "../lib/format";
import type {SearchItem, SearchResponse, SelectionResponse} from "../types";
import {Feedback} from "../components/ui/Feedback";
import {ProductPhoto} from "../components/ui/ProductPhoto";

const suggestions = ["Mouse gamer", "Notebooks", "Fones", "Teclado"];

function ProductCard({item, selected, onToggle}: {
  item: SearchItem; selected: boolean; onToggle: () => void;
}) {
  return <button type="button" className={"catalog-card min-w-0 touch-manipulation "+(selected?"selected":"")} onClick={onToggle}
    aria-pressed={selected}>
    <span className={"checkmark "+(selected?"on":"")}>{selected&&<Check size={14}/>}</span>
    <ProductPhoto url={item.image_url} title={item.title}/>
    <div className="catalog-card-body min-w-0">
      <span className="catalog-tag">MERCADO LIVRE · PRODUTO</span>
      <strong title={item.title}>{item.title}</strong>
      {item.reference_price_cents!==null && item.reference_price_cents!==undefined && item.reference_price_cents>item.price_cents
        ? <div className="flex min-w-0 flex-col gap-1.5">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="text-xs text-slate-500">De: <s>{formatBrl(item.reference_price_cents)}</s></span>
              {item.discount_percent!==null && item.discount_percent!==undefined && item.discount_percent>0 &&
                <span className="rounded-md bg-emerald-100 px-2 py-0.5 text-[11px] font-extrabold text-emerald-800">{item.discount_percent}% OFF</span>}
            </div>
            <span className="text-xs font-semibold text-slate-500">Por:</span>
            <span className="catalog-price text-xl font-extrabold text-emerald-700 sm:text-2xl">{formatBrl(item.price_cents)}</span>
          </div>
        : <span className="catalog-price text-base sm:text-xl">{formatBrl(item.price_cents)}</span>}
      <span className="catalog-meta">Preços anunciados via provedor externo; confira antes de publicar</span>
      <span className="catalog-select">{selected?"Selecionado":"Selecionar produto"} <ArrowRight size={14}/></span>
    </div>
  </button>;
}

export function DiscoveryPage({onOpenOffer}: {
  onOpenOffer:(offerId:string)=>void;
}) {
  const [query,setQuery]=useState("");
  const [result,setResult]=useState<SearchResponse|null>(null);
  const [selected,setSelected]=useState<Set<string>>(()=>new Set());
  const [searching,setSearching]=useState(false);
  const [saving,setSaving]=useState(false);
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");

  async function runSearch(value:string) {
    const term=value.trim();
    if(term.length<2)return;
    setQuery(term);setSearching(true);setError("");setNotice("");setResult(null);setSelected(new Set());
    try {
      const response=await apiRequest<SearchResponse>("/api/v1/discovery/search",{
        method:"POST",body:{query:term,limit:20},
      });
      setResult(response);
    }catch(err){setError(errorMessage(err));}
    finally{setSearching(false);}
  }
  function handleSearch(event:FormEvent<HTMLFormElement>){event.preventDefault();void runSearch(query);}
  function toggle(id:string){
    setSelected(previous=>{
      const next=new Set(previous);
      if(next.has(id))next.delete(id);else next.add(id);
      return next;
    });
  }
  async function saveSelection(){
    if(!result||selected.size===0)return;
    setSaving(true);setError("");setNotice("");
    try {
      const response=await apiRequest<SelectionResponse>("/api/v1/discovery/select",{
        method:"POST",body:{search_id:result.search_id,source_item_ids:Array.from(selected)},
      });
      const first=response.selected[0];
      setNotice(response.selected.length+" produto(s) enviado(s) para revisão, sem publicação.");
      setSelected(new Set());
      if(first)onOpenOffer(first.offer_id);
    }catch(err){setError(errorMessage(err));}
    finally{setSaving(false);}
  }

  return <div className="discovery-layout flex min-w-0 flex-col gap-5">
    <section className="discovery-hero relative min-h-0 overflow-hidden rounded-2xl lg:min-h-[284px]">
      <span className="hero-orbit hero-orbit-1" aria-hidden="true"/><span className="hero-orbit hero-orbit-2" aria-hidden="true"/>
      <div className="hero-content min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-9">
        <div className="hero-badge"><Sparkles size={14}/> CURADORIA INTELIGENTE</div>
        <h2 className="text-[21px] sm:text-2xl">Encontre produtos.<br/><span>Escolha o que compartilhar.</span></h2>
        <p>Encontre anúncios com desconto informado e selecione as melhores ofertas para revisão.</p>
        <form onSubmit={handleSearch} className="hero-search flex w-full min-w-0 flex-wrap items-center gap-3 sm:flex-nowrap">
          <Search size={20} color="#5280ac" className="shrink-0"/>
          <input className="min-w-0 flex-[1_1_calc(100%-40px)] text-base sm:flex-1 sm:text-sm" aria-label="Buscar produtos" placeholder="Ex.: mouse gamer, notebook, fones..." value={query}
            onChange={e=>setQuery(e.target.value)} maxLength={100} minLength={2} required/>
          <button type="submit" disabled={searching||query.trim().length<2} className="button primary min-h-11 w-full sm:w-auto">
            {searching?"Buscando...":"Buscar ofertas"}<ArrowRight size={17}/>
          </button>
        </form>
        <div className="suggestions flex flex-wrap items-center gap-2"><span>Experimente:</span>{suggestions.map(text=><button type="button" key={text} onClick={()=>void runSearch(text)} disabled={searching}>{text}</button>)}</div>
      </div>
      <div className="hero-illustration hidden lg:flex" aria-hidden="true"><div className="hero-glyph"><PackageSearch size={80} strokeWidth={1.2}/></div><span className="hero-spark s1">✧</span><span className="hero-spark s2">✳</span></div>
    </section>

    {error&&<Feedback tone="error" onClose={()=>setError("")}>{error}{error.includes("APIFY_TOKEN")&&<span> Configure APIFY_TOKEN no servidor para habilitar a busca ao vivo.</span>}</Feedback>}
    {notice&&<Feedback tone="success" onClose={()=>setNotice("")}>{notice}</Feedback>}
    {!result&&!searching&&<div className="discovery-empty">
      <span className="empty-graphic"><MousePointer2 size={24}/></span>
      <strong>Pronto para encontrar a próxima oferta?</strong>
      <p>Digite um nicho para consultar anúncios via provedor externo configurado.</p>
    </div>}
    {searching&&<div className="loading-card"><div className="spinner"/><p>Buscando anúncios no Mercado Livre...</p></div>}
    {result&&<section className="results">
      <div className="results-header flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div><div className="eyebrow">RESULTADO DA BUSCA</div><h2>{result.items.length} {result.live?`promoção${result.items.length===1?"":"ões"} encontrada${result.items.length===1?"":"s"}`:`produto${result.items.length===1?"":"s"} encontrado${result.items.length===1?"":"s"}`}</h2><p>Para “{result.query}” · {result.live ? 'coleta terceirizada (Apify)' : 'catálogo CSV local'}</p></div>
        <div className="results-info"><Clock3 size={15}/> Seleção válida por 45 min</div>
      </div>
      {result.items.length===0?<div className="empty-panel"><PackageSearch size={30}/><h3>Nenhuma promoção identificada</h3><p>{result.live?"Não encontramos anúncios com preço original maior que o preço atual nesta consulta. Tente outra palavra-chave.":"Tente outro termo ou atualize o catálogo autorizado."}</p></div>:
      <>
        <div className="results-controls flex flex-wrap items-center justify-between gap-2"><span>{selected.size} de {result.items.length} selecionado(s)</span>
          <button type="button" className="text-button" onClick={()=>setSelected(selected.size===result.items.length?new Set():new Set(result.items.map(item=>item.source_item_id)))}><CheckCheck size={15}/>{selected.size===result.items.length?"Desmarcar todos":"Selecionar todos"}</button></div>
        <div className="catalog-grid grid grid-cols-1 gap-3 min-[370px]:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{result.items.map(item=><ProductCard key={item.source_item_id} item={item} selected={selected.has(item.source_item_id)} onToggle={()=>toggle(item.source_item_id)}/>)}</div>
        <div className="selection-tray sticky bottom-[calc(5.5rem+env(safe-area-inset-bottom))] z-40 flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between md:bottom-5"><span><strong>{selected.size}</strong> produto(s) na seleção <small>Criação de rascunhos — sem envio</small></span><button type="button" className="button primary min-h-11 w-full sm:w-auto" onClick={()=>void saveSelection()} disabled={saving||selected.size===0}>{saving?"Salvando...":"Revisar selecionados"}<ArrowRight size={17}/></button></div>
      </>}
    </section>}
    <div className="source-footnote flex flex-wrap items-start gap-2"><Sparkles size={15}/> A busca {result ? (result.live ? <>consulta um <strong>scraper terceirizado (Apify)</strong></> : <>usa <strong>catálogo CSV local</strong></>) : <>consulta a <strong>fonte configurada no servidor</strong></>}. O preço original é o valor riscado informado pelo anúncio, não um histórico verificado. Confira preço, estoque e desconto antes de publicar.</div>
  </div>;
}
