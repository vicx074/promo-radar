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
  return <button type="button" className={"catalog-card "+(selected?"selected":"")} onClick={onToggle}
    aria-pressed={selected}>
    <span className={"checkmark "+(selected?"on":"")}>{selected&&<Check size={14}/>}</span>
    <ProductPhoto url={item.image_url} title={item.title}/>
    <div className="catalog-card-body">
      <span className="catalog-tag">MERCADO LIVRE · CATÁLOGO</span>
      <strong title={item.title}>{item.title}</strong>
      <span className="catalog-price">{formatBrl(item.price_cents)}</span>
      <span className="catalog-meta">Preço informado no catálogo · desconto não verificado</span>
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

  return <div className="discovery-layout">
    <section className="discovery-hero">
      <span className="hero-orbit hero-orbit-1" aria-hidden="true"/><span className="hero-orbit hero-orbit-2" aria-hidden="true"/>
      <div className="hero-content">
        <div className="hero-badge"><Sparkles size={14}/> CURADORIA INTELIGENTE</div>
        <h2>Encontre produtos.<br/><span>Escolha o que compartilhar.</span></h2>
        <p>Busque no seu catálogo e monte uma seleção de ofertas com poucos cliques.</p>
        <form onSubmit={handleSearch} className="hero-search">
          <Search size={20} color="#5280ac"/>
          <input aria-label="Buscar produtos" placeholder="Ex.: mouse gamer, notebook, fones..." value={query}
            onChange={e=>setQuery(e.target.value)} maxLength={100} minLength={2} required/>
          <button type="submit" disabled={searching||query.trim().length<2} className="button primary">
            {searching?"Buscando...":"Buscar ofertas"}<ArrowRight size={17}/>
          </button>
        </form>
        <div className="suggestions"><span>Experimente:</span>{suggestions.map(text=><button type="button" key={text} onClick={()=>void runSearch(text)} disabled={searching}>{text}</button>)}</div>
      </div>
      <div className="hero-illustration" aria-hidden="true"><div className="hero-glyph"><PackageSearch size={80} strokeWidth={1.2}/></div><span className="hero-spark s1">✧</span><span className="hero-spark s2">✳</span></div>
    </section>

    {error&&<Feedback tone="error" onClose={()=>setError("")}>{error}{error.includes("Catálogo local")&&<span> Coloque o CSV autorizado em <code>data/import/catalogo.csv</code> no backend.</span>}</Feedback>}
    {notice&&<Feedback tone="success" onClose={()=>setNotice("")}>{notice}</Feedback>}
    {!result&&!searching&&<div className="discovery-empty">
      <span className="empty-graphic"><MousePointer2 size={24}/></span>
      <strong>Pronto para encontrar a próxima oferta?</strong>
      <p>Digite um nicho para consultar seu catálogo. A busca não acessa anúncios ao vivo do Mercado Livre.</p>
    </div>}
    {searching&&<div className="loading-card"><div className="spinner"/><p>Consultando os produtos do seu catálogo...</p></div>}
    {result&&<section className="results">
      <div className="results-header">
        <div><div className="eyebrow">RESULTADO DA BUSCA</div><h2>{result.items.length} produto{result.items.length===1?"":"s"} encontrado{result.items.length===1?"":"s"}</h2><p>Para “{result.query}” · resultados do arquivo local autorizado</p></div>
        <div className="results-info"><Clock3 size={15}/> Seleção válida por 45 min</div>
      </div>
      {result.items.length===0?<div className="empty-panel"><PackageSearch size={30}/><h3>Nenhum produto encontrado</h3><p>Tente outro termo ou atualize o catálogo autorizado.</p></div>:
      <>
        <div className="results-controls"><span>{selected.size} de {result.items.length} selecionado(s)</span>
          <button type="button" className="text-button" onClick={()=>setSelected(selected.size===result.items.length?new Set():new Set(result.items.map(item=>item.source_item_id)))}><CheckCheck size={15}/>{selected.size===result.items.length?"Desmarcar todos":"Selecionar todos"}</button></div>
        <div className="catalog-grid">{result.items.map(item=><ProductCard key={item.source_item_id} item={item} selected={selected.has(item.source_item_id)} onToggle={()=>toggle(item.source_item_id)}/>)}</div>
        <div className="selection-tray"><span><strong>{selected.size}</strong> produto(s) na seleção <small>Criação de rascunhos — sem envio</small></span><button type="button" className="button primary" onClick={()=>void saveSelection()} disabled={saving||selected.size===0}>{saving?"Salvando...":"Revisar selecionados"}<ArrowRight size={17}/></button></div>
      </>}
    </section>}
    <div className="source-footnote"><Sparkles size={15}/> A busca consulta apenas <strong>CSV local autorizado</strong>. Preços, estoques e descontos não são verificados em tempo real.</div>
  </div>;
}
