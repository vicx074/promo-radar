import {ImageOff} from "lucide-react";
import {useState} from "react";
import {safeProductImage} from "../../lib/format";

export function ProductPhoto({url, title}: {url: string | null; title: string}) {
  const [failed, setFailed] = useState(false);
  const src = safeProductImage(url);
  if (!src || failed) return <div className="product-photo photo-fallback"><ImageOff size={25} /><span>Sem imagem</span></div>;
  return <div className="product-photo"><img src={src} alt={title} loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} /></div>;
}
