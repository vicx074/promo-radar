export type Section = "discovery" | "offers" | "groups" | "campaigns" | "history" | "settings";

export type OfferStatus = "DRAFT" | "APPROVED";
export interface Offer {
  id: string;
  source: string;
  source_item_id: string;
  title: string;
  price_cents: number;
  reference_price_cents: number | null;
  status: OfferStatus;
  product_url: string | null;
  affiliate_url: string | null;
  affiliate_status: string;
  image_url: string | null;
  created_at: string;
}
export interface SearchItem {
  source_item_id: string;
  title: string;
  price_cents: number;
  product_url: string;
  image_url: string | null;
  promotion_verified: boolean;
  price_history_available: boolean;
}
export interface SearchResponse {
  search_id: string;
  query: string;
  source: string;
  expires_at: string;
  items: SearchItem[];
}
export interface SelectionResponse {
  selected: Array<{source_item_id: string; offer_id: string; status: OfferStatus; created: boolean}>;
}
export interface OfferPreview {
  message: string;
  image_url: string | null;
  image_ready: boolean;
  image: {size_bytes: number; mime_type: string; width: number; height: number} | null;
}
export interface AffiliateConnection {
  provider: string;
  status: "DISCONNECTED" | "CONNECTED";
  connected: boolean;
  auto_generation_available: boolean;
  permissions: string[];
  connection_method: string;
}
export interface Publication {
  id: string;
  offer_id: string;
  status: "SENDING" | "SENT" | "UNKNOWN";
  created_at: string;
  updated_at: string;
  provider_message_id: string | null;
  error_summary: string | null;
}

export interface OwnerSession {
  authenticated: boolean;
  csrf_token: string;
  expires_at: number;
}
