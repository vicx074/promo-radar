import {AlertCircle, CheckCircle2, Info, X} from "lucide-react";
import type {ReactNode} from "react";

export function Feedback({
  children, tone = "info", onClose,
}: {children: ReactNode; tone?: "info" | "error" | "success"; onClose?: () => void}) {
  const Symbol = tone === "error" ? AlertCircle : tone === "success" ? CheckCircle2 : Info;
  return <div className={"feedback feedback-" + tone} role={tone === "error" ? "alert" : "status"}>
    <Symbol size={17} aria-hidden="true" />
    <div>{children}</div>
    {onClose && <button type="button" className="icon-button feedback-close" onClick={onClose} aria-label="Fechar aviso"><X size={16} /></button>}
  </div>;
}
