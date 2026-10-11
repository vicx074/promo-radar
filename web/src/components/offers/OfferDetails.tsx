import {useEffect,useState,type FormEvent} from "react";
import {
  BadgeCheck,CheckCircle2,ClipboardList,ExternalLink,ImagePlus,Link2, Send,
  ShieldAlert,Sparkles,
} from "lucide-react";
import {apiRequest,errorMessage} from "../../lib/api";
import {formatBrl} from "../../lib/format";
import type {Offer,OfferPreview,Publication} from "../../types";
import {Feedback} from "../ui/Feedback";
import {ProductPhoto} from "../ui/ProductPhoto";

export function OfferDetails({adminKey,offerId,onUpdated}:{
  adminKey:string;offerId:string;onUpdated:()=>void;
}) {
  const [offer,setOffer]=useState<Offer|null>(null);
  const [preview,setPreview]=useState<OfferPreview|null>(null);
  const [loading,setLoading]=useState(true);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState("");
  const [success,setSuccess]=useState("");
  const [link,setLink]=useState("");
  const [confirmed,setConfirmed]=useState(false);
  const [permission,setPermission]=useState(false);

  async function load() {
    setLoading(true);setError("");setSuccess("");
    try {
      const [o,p]=await Promise.all([
        apiRequest<Offer>(adminKey,"/api/v1/offers/"+encodeURIComponent(offerId)),
        apiRequest<OfferPreview>(adminKey,"/api/v1/offers/"+encodeURIComponent(offerId)+"/preview"),
      ]);
      setOffer(o);setPreview(p);
    }catch(err){setError(errorMessage(err));}
    finally{setLoading(false);}
  }
  useEffect(()=>{void load();},[offerId,adminKey]);

  async function execute(task:()=>Promise<void>){
    setBusy(true);setError("");setSuccess("");
    try{await task();}
    catch(err){setError(errorMessage(err));}
    finally{setBusy(false);}
  }

  function saveLink(event:FormEvent) {
    event.preventDefault();
    if(!confirmed||!link.trim())return;
    void execute(async()=>{
      const o=await apiRequest<Offer>(adminKey,
        "/api/v1/offers/"+encodeURIComponent(offerId)+"/affiliate-link",{
          method:"POST",body:{affiliate_url:link.trim(),product_match_confirmed:true},
        });
      setOffer(o);
      setPreview(await apiRequest<OfferPreview>(adminKey,"/api/v1/offers/"+encodeURIComponent(offerId)+"/preview"));
      setLink("");setConfirmed(false);
      setSuccess("Link cadastrado como informado por você. O formato não comprova comissão.");
      onUpdated();
    });
  }

  function prepareImage(){
    void execute(async()=>{
      await apiRequest(adminKey,"/api/v1/offers/"+encodeURIComponent(offerId)+"/prepare-media",{method:"POST"});
      setPreview(await apiRequest<OfferPreview>(adminKey,"/api/v1/offers/"+encodeURIComponent(offerId)+"/preview"));
      setSuccess("Imagem otimizada com sucesso e pronta para revisão.");
    });
  }

  function approve(){
    void execute(async()=>{
      const o=await apiRequest<Offer>(adminKey,"/api/v1/offers/"+encodeURIComponent(offerId)+"/approve",{method:"POST"});
      setOffer(o);
      setSuccess("Oferta aprovada. Nenhuma mensagem foi enviada.");
      onUpdated();
    });
  }

  function publish(){
    if(!permission||!window.confirm("Confirma a publicação manual desta oferta no grupo configurado no backend? Verifique antes se o destino é permitido."))return;
    void execute(async()=>{
      const response=await apiRequest<Publication>(adminKey,
        "/api/v1/offers/"+encodeURIComponent(offerId)+"/publish",{method:"POST"});
      setSuccess("Aceite pela Evolution registrado (não confirma entrega). Publicação ID: "+response.id);
      setPermission(false);
    });
  }

  if(loading)return <aside className="card detail-card"><div className="loading-card compact"><div className="spinner"/>Carregando detalhes...</div></aside>;
  if(!offer)return <aside className="card detail-card"><Feedback tone="error">{error||"Oferta indisponível"}</Feedback></aside>;
  const isMl=offer.source==="mercado_livre";
  const canLink=isMl&&offer.status==="DRAFT";
  const noLink=isMl&&!offer.affiliate_url;
  const needsMedia=!!offer.image_url&&!preview?.image_ready;
  const canApprove=offer.status==="DRAFT"&&!noLink&&!needsMedia;
  const canPublish=offer.status==="APPROVED"&&!noLink&&!needsMedia;

  return <aside className="card detail-card" aria-label="Detalhes da oferta selecionada">
    <div className="detail-head"><div><div className="eyebrow">DETALHES DA OFERTA</div><h2>Revisão & publicação</h2></div><ClipboardList size={20}/></div>
    {error&&<Feedback tone="error" onClose={()=>setError("")}>{error}</Feedback>}
    {success&&<Feedback tone="success" onClose={()=>setSuccess("")}>{success}</Feedback>}
    <div className="detail-product"><ProductPhoto url={offer.image_url} title={offer.title}/><span><strong>{offer.title}</strong><span>{formatBrl(offer.price_cents)}</span></span></div>
    <div className="detail-links"><div><span>Endereço do produto</span>{offer.product_url?
      <a href={offer.product_url} target="_blank" rel="noreferrer noopener">Abrir produto <ExternalLink size={13}/></a>:<small>Não informado</small>}</div>
      <div><span>Link de afiliado</span>{offer.affiliate_url?
        <span className="registered-link"><Link2 size={15}/><span title={offer.affiliate_url}>{offer.affiliate_url}</span></span>:
        <span className="missing-link">Não cadastrado</span>}</div>
    </div>
    {canLink&&<form className="affiliate-form" onSubmit={saveLink}>
      <div className="form-subtitle"><Link2 size={17}/> Cadastrar link de afiliado</div>
      <p>Gere o link na Central de Afiliados e cole aqui o endereço correspondente a este produto.</p>
      <label htmlFor={"link-"+offer.id}>Link de divulgação</label>
      <input id={"link-"+offer.id} type="url" required autoComplete="off" spellCheck={false}
        placeholder="https://meli.la/..." value={link} onChange={e=>setLink(e.target.value)} />
      <label className="check-label"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>
        <span>Confirmo que gerei este link para o produto acima.</span></label>
      <button className="button secondary full" disabled={busy||!link.trim()||!confirmed} type="submit"><Link2 size={16}/>{offer.affiliate_url?"Atualizar link":"Salvar link"}</button>
      <small>A plataforma valida somente o formato, não a titularidade ou o rastreamento.</small>
    </form>}
    {isMl&&!offer.affiliate_url&&offer.status==="APPROVED"&&<Feedback tone="error">Esta oferta antiga foi aprovada antes da separação dos links. Por segurança, sua publicação permanece bloqueada. Crie um novo rascunho e vincule o link correto.</Feedback>}
    <div className="review-steps">
      <div className="review-step"><span className={"step-icon "+(!noLink?"done":"")}>{!noLink?<CheckCircle2 size={17}/>:<Link2 size={17}/>}</span>
        <span><strong>Link de divulgação</strong><small>{noLink?"Cadastre antes de aprovar":isMl?"Link informado pelo operador":"Link legado sem verificação"}</small></span></div>
      <div className="review-step"><span className={"step-icon "+(!needsMedia?"done":"")}>{!needsMedia?<CheckCircle2 size={17}/>:<ImagePlus size={17}/>}</span>
        <span><strong>Imagem da promoção</strong><small>{!offer.image_url?"Sem imagem associada":needsMedia?"Precisa preparar imagem":"Imagem pronta para publicar"}</small></span>
        {offer.status==="DRAFT"&&needsMedia&&<button type="button" className="text-button" disabled={busy} onClick={prepareImage}>Preparar</button>}</div>
      <div className="review-step"><span className={"step-icon "+(offer.status==="APPROVED"?"done":"")}>{offer.status==="APPROVED"?<CheckCircle2 size={17}/>:<BadgeCheck size={17}/>}</span>
        <span><strong>Aprovação humana</strong><small>{offer.status==="APPROVED"?"Aprovada":"Aguardando sua revisão"}</small></span>
      </div>
    </div>
    <div className="preview-section"><div className="preview-header"><Sparkles size={16}/><strong>Prévia da mensagem</strong></div>
      <pre>{preview?.message??"Prévia indisponível"}</pre></div>
    {offer.status==="DRAFT"&&<button className="button primary full" type="button" disabled={busy||!canApprove} onClick={approve}><BadgeCheck size={17}/>{busy?"Processando...":"Aprovar oferta"}</button>}
    {offer.status==="APPROVED"&&<div className="publish-box">
      <div className="publish-title"><Send size={17}/> Publicação manual</div>
      <p>Utiliza o grupo configurado no backend. O envio automático ainda não existe.</p>
      <label className="check-label"><input type="checkbox" checked={permission} onChange={e=>setPermission(e.target.checked)}/><span>Confirmei que o destino é permitido e que tenho autorização para publicar.</span></label>
      <button className="button primary full" type="button" disabled={busy||!canPublish||!permission} onClick={publish}><Send size={16}/> {busy?"Processando...":"Publicar agora"}</button>
      <div className="safety-text"><ShieldAlert size={14}/> Requer SEND_ENABLED=true; HTTP 2xx não confirma entrega.</div>
    </div>}
  </aside>;
}
