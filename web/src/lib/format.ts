export function formatBrl(cents: number): string {
  return new Intl.NumberFormat("pt-BR", {style: "currency", currency: "BRL"}).format(cents / 100);
}
export function formatDate(date: string): string {
  const parsed = new Date(date);
  return Number.isNaN(parsed.valueOf())
    ? "Data indisponível"
    : new Intl.DateTimeFormat("pt-BR", {day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit"}).format(parsed);
}
export function safeProductImage(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && url.hostname === "http2.mlstatic.com" &&
      !url.username && !url.password && !url.port ? url.toString() : null;
  } catch {
    return null;
  }
}
