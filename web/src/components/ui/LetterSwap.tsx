import {useState} from "react";
import {motion, stagger, useAnimate, useReducedMotion} from "motion/react";

/**
 * Adaptação do conceito Letter Swap, Fancy Components (Daniel Petho, licença MIT).
 * Fonte: https://github.com/danielpetho/fancy/tree/main/src/fancy/components/text
 * Texto acessível para leitores de tela; desativa animação com reduced motion.
 */
export function LetterSwap({text}: {text: string}) {
  const [scope, animate] = useAnimate();
  const [busy, setBusy] = useState(false);
  const reduceMotion = useReducedMotion();

  function play() {
    if (busy || reduceMotion) return;
    setBusy(true);
    void Promise.all([
      animate(".swap-top", {y: "-100%"}, {duration: 0.43, delay: stagger(0.018)}),
      animate(".swap-bottom", {top: "0%"}, {duration: 0.43, delay: stagger(0.018)}),
    ]).then(() => {
      void animate(".swap-top", {y: "0%"}, {duration: 0});
      void animate(".swap-bottom", {top: "100%"}, {duration: 0});
      setBusy(false);
    }).catch(() => setBusy(false));
  }

  return (
    <span className="letter-swap" onMouseEnter={play} ref={scope}>
      <span className="sr-only">{text}</span>
      {Array.from(text).map((char, i) => (
        <span key={i} className="swap-char" aria-hidden="true">
          <motion.span className="swap-top">{char === " " ? "\u00a0" : char}</motion.span>
          <motion.span className="swap-bottom">{char === " " ? "\u00a0" : char}</motion.span>
        </span>
      ))}
    </span>
  );
}
