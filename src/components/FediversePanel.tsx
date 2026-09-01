import React, { useState, useEffect, useRef } from "react";
import { sanitizeFediverseHtml } from "@/lib/sanitizeHtml";
import {
  Share2, Globe, Home, Bell, User, Plus, Loader2, Sparkles,
  Check, Send, FileText, MessageSquare, Heart, Repeat, ArrowLeft,
  Search, UserPlus, UserCheck, Eye, EyeOff, X, Maximize2, ExternalLink
} from "lucide-react";

interface FediversoAccount {
  id: string;
  instance_url: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
}

interface MastodonSearchAccount {
  id: string;
  username: string;
  acct: string;
  display_name: string;
  avatar: string;
  note: string;
  followers_count: number;
  following_count: number;
  statuses_count: number;
  url: string;
}

interface MediaAttachment {
  id: string;
  type: "image" | "gifv" | "video" | "audio" | "unknown";
  url: string;
  preview_url: string;
  remote_url?: string | null;
  description?: string | null;
  blurhash?: string | null;
}

interface CardPreview {
  url: string;
  title: string;
  description: string;
  type: string;
  image?: string | null;
  provider_name?: string | null;
}

interface Toot {
  id: string;
  created_at: string;
  content: string;
  spoiler_text?: string;
  sensitive?: boolean;
  account: {
    username: string;
    acct: string;
    display_name: string;
    avatar: string;
  };
  media_attachments?: MediaAttachment[];
  card?: CardPreview | null;
  reblog?: Toot | null;
  reblogs_count: number;
  favourites_count: number;
  replies_count: number;
}

export function FediversePanel() {
  const [accounts, setAccounts] = useState<FediversoAccount[]>([]);
  const [activeAccount, setActiveAccount] = useState<FediversoAccount | null>(null);
  const [feed, setFeed] = useState<Toot[]>([]);
  const [feedType, setFeedType] = useState<"home" | "local" | "public" | "notifications" | "search">("home");
  const [loadingFeed, setLoadingFeed] = useState(false);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  
  // Media & Lightbox state
  const [selectedMedia, setSelectedMedia] = useState<{ url: string; alt?: string } | null>(null);
  const [revealedSensitive, setRevealedSensitive] = useState<{ [key: string]: boolean }>({});
  const [expandedSpoilers, setExpandedSpoilers] = useState<{ [key: string]: boolean }>({});
  
  // Account search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MastodonSearchAccount[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);
  const [followingMap, setFollowingMap] = useState<{ [key: string]: boolean }>({});

  // Registering instance state
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [instanceInput, setInstanceInput] = useState("");
  const [registeringInstance, setRegisteringInstance] = useState(false);
  const [isConnectingOAuth, setIsConnectingOAuth] = useState(false);

  // Editor and AI state
  const [tootText, setTootText] = useState("");
  const [inReplyTo, setInReplyTo] = useState<Toot | null>(null);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [activeSummary, setActiveSummary] = useState<string | null>(null);

  // Helper to obtain auth headers from localStorage token
  const getAuthHeaders = (extra: Record<string, string> = {}) => {
    const token = typeof window !== "undefined" ? localStorage.getItem("authToken") : null;
    return {
      ...extra,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  // Check URL parameters for OAuth Callback on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");
    const state = urlParams.get("state");
    let client_id = urlParams.get("client_id");
    let instance_url = urlParams.get("instance_url");

    if ((!client_id || !instance_url) && state) {
      try {
        const parsed = JSON.parse(decodeURIComponent(state));
        instance_url = instance_url || parsed.instance_url || parsed.instance;
        client_id = client_id || parsed.client_id;
      } catch {
        try {
          const parsed = JSON.parse(state);
          instance_url = instance_url || parsed.instance_url || parsed.instance;
          client_id = client_id || parsed.client_id;
        } catch (e) {
          console.error("Error parsing OAuth state:", e);
        }
      }
    }

    if (!instance_url && typeof window !== "undefined") {
      instance_url = localStorage.getItem("fediverso_temp_instance");
    }
    if (!client_id && typeof window !== "undefined") {
      client_id = localStorage.getItem("fediverso_temp_client_id");
    }

    if (code && client_id && instance_url) {
      setIsConnectingOAuth(true);
      handleOAuthCallback(code, client_id, instance_url);
    } else {
      fetchAccounts();
    }
  }, []);

  // Fetch feed when active account or feed type changes
  useEffect(() => {
    if (activeAccount && feedType !== "search") {
      fetchFeed(activeAccount.id, feedType);
    } else if (!activeAccount) {
      setFeed([]);
    }
  }, [activeAccount, feedType]);

  const fetchAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const resp = await fetch("/api/fediverso/accounts", { headers: getAuthHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        setAccounts(data);
        if (data.length > 0 && !activeAccount) {
          setActiveAccount(data[0]);
        }
      }
    } catch (err) {
      console.error("Error fetching accounts:", err);
    } finally {
      setLoadingAccounts(false);
    }
  };

  const handleOAuthCallback = async (code: string, client_id: string, instance_url: string) => {
    const redirect_uri = `${window.location.origin}/fediverso`;
    try {
      const resp = await fetch("/api/fediverso/callback", {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ code, client_id, instance_url, redirect_uri })
      });
      if (resp.ok) {
        localStorage.removeItem("fediverso_temp_instance");
        localStorage.removeItem("fediverso_temp_client_id");
        // Clean URL params
        window.history.replaceState({}, document.title, window.location.pathname);
        await fetchAccounts();
      } else {
        const errData = await resp.json();
        alert(`Error al conectar cuenta: ${errData.detail || "Fallo desconocido"}`);
      }
    } catch (err) {
      console.error("Error handling OAuth callback:", err);
      alert("Error al comunicarse con el servidor durante la autenticación");
    } finally {
      setIsConnectingOAuth(false);
    }
  };

  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!instanceInput.trim()) return;

    setRegisteringInstance(true);
    try {
      const redirect_uri = `${window.location.origin}/fediverso`;
      const resp = await fetch("/api/fediverso/register-instance", {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ instance_url: instanceInput, redirect_uri })
      });

      if (resp.ok) {
        const data = await resp.json();
        
        // Save temporary client details in localStorage to verify on callback
        localStorage.setItem("fediverso_temp_instance", data.instance_url);
        localStorage.setItem("fediverso_temp_client_id", data.client_id);
        
        window.location.href = data.authorize_url;
      } else {
        const errData = await resp.json();
        alert(`Error al registrar instancia: ${errData.detail || "Fallo desconocido"}`);
      }
    } catch (err) {
      console.error("Error registering instance:", err);
    } finally {
      setRegisteringInstance(false);
    }
  };

  const fetchFeed = async (accountId: string, type: string) => {
    setLoadingFeed(true);
    try {
      const resp = await fetch(`/api/fediverso/feed?account_id=${accountId}&feed_type=${type}`, { headers: getAuthHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        setFeed(data);
      }
    } catch (err) {
      console.error("Error fetching feed:", err);
    } finally {
      setLoadingFeed(false);
    }
  };

  const handleSearchAccounts = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!activeAccount || !searchQuery.trim()) return;

    setLoadingSearch(true);
    try {
      const resp = await fetch(`/api/fediverso/search/accounts?account_id=${activeAccount.id}&query=${encodeURIComponent(searchQuery)}`, { headers: getAuthHeaders() });
      if (resp.ok) {
        const data = await resp.json();
        setSearchResults(data);
      } else {
        console.error("Error searching accounts");
      }
    } catch (err) {
      console.error("Error performing account search:", err);
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleToggleFollow = async (targetAccountId: string) => {
    if (!activeAccount) return;
    const isFollowing = followingMap[targetAccountId];
    const endpoint = isFollowing ? "/api/fediverso/accounts/unfollow" : "/api/fediverso/accounts/follow";

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          account_id: activeAccount.id,
          target_mastodon_account_id: targetAccountId
        })
      });

      if (resp.ok) {
        setFollowingMap((prev) => ({ ...prev, [targetAccountId]: !isFollowing }));
      }
    } catch (err) {
      console.error("Error toggling follow status:", err);
    }
  };

  const handlePublishToot = async () => {
    if (!activeAccount || !tootText.trim()) return;

    try {
      const resp = await fetch("/api/fediverso/toot", {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          account_id: activeAccount.id,
          status: tootText,
          in_reply_to_id: inReplyTo?.id || null
        })
      });

      if (resp.ok) {
        setTootText("");
        setInReplyTo(null);
        fetchFeed(activeAccount.id, feedType);
      } else {
        alert("Fallo al publicar el toot.");
      }
    } catch (err) {
      console.error("Error publishing toot:", err);
    }
  };

  const handleAiCompose = async () => {
    if (!aiPrompt.trim()) return;

    setAiLoading(true);
    try {
      const resp = await fetch("/api/fediverso/ai/compose", {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          prompt: aiPrompt,
          context: inReplyTo ? `Respondiendo a ${inReplyTo.account.acct}: "${inReplyTo.content}"` : null
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setTootText(data.draft);
      }
    } catch (err) {
      console.error("AI compose error:", err);
    } finally {
      setAiLoading(false);
    }
  };

  const handleAiImprove = async () => {
    if (!tootText.trim()) return;

    setAiLoading(true);
    try {
      const resp = await fetch("/api/fediverso/ai/compose", {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          prompt: `Reescribe y mejora este toot: "${tootText}"`
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setTootText(data.draft);
      }
    } catch (err) {
      console.error("AI improve error:", err);
    } finally {
      setAiLoading(false);
    }
  };

  const handleSummarizeThread = async (statusId: string) => {
    if (!activeAccount) return;

    setSummaryLoading(true);
    setActiveSummary(statusId);
    try {
      const resp = await fetch("/api/fediverso/ai/summarize-thread", {
        method: "POST",
        headers: getAuthHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({
          account_id: activeAccount.id,
          status_id: statusId
        })
      });

      if (resp.ok) {
        const data = await resp.json();
        setAiResult(data.summary);
      } else {
        alert("No se pudo obtener el resumen de la IA.");
      }
    } catch (err) {
      console.error("AI summary error:", err);
    } finally {
      setSummaryLoading(false);
    }
  };

  if (isConnectingOAuth) {
    return (
      <div className="flex h-[50vh] w-full flex-col items-center justify-center gap-4 bg-card/30 backdrop-blur-md border border-border/40 rounded-3xl p-8 shadow-xl text-center">
        <div className="p-4 rounded-2xl bg-primary/10 text-primary">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
        </div>
        <div className="space-y-1">
          <h3 className="text-xl font-bold text-foreground">Conectando cuenta del Fediverso</h3>
          <p className="text-sm text-muted-foreground">
            Verificando credenciales y vinculando tu perfil de Mastodon...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[600px]">
      
      {/* Feed Panel (Left Side) */}
      <div className="lg:col-span-7 flex flex-col space-y-4 bg-card/30 backdrop-blur-md border border-border/40 rounded-2xl p-6 shadow-xl">
        {/* Selector de cuenta y Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-border/20 pb-4 gap-4">
          <div className="flex items-center space-x-3">
            {accounts.length > 0 ? (
              <div className="relative">
                <select
                  className="bg-secondary/40 text-sm font-medium border border-border/30 rounded-xl px-3 py-2 pr-8 appearance-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground cursor-pointer"
                  value={activeAccount?.id || ""}
                  onChange={(e) => {
                    const acc = accounts.find((a) => a.id === e.target.value);
                    if (acc) setActiveAccount(acc);
                  }}
                >
                  {accounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.display_name || acc.username} ({acc.instance_url.replace("https://", "")})
                    </option>
                  ))}
                </select>
                <div className="absolute right-3 top-3 pointer-events-none w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Sin cuentas conectadas</p>
            )}
            
            <button
              onClick={() => setShowAddAccount(!showAddAccount)}
              className="p-2 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 hover:border-primary/40 rounded-xl transition-all duration-300 flex items-center justify-center"
              title="Conectar nueva cuenta"
            >
              <Plus className="h-4 w-4" />
            </button>
          </div>

          {/* Feed Switcher Tabs */}
          <div className="flex bg-secondary/20 border border-border/20 rounded-xl p-1 text-xs overflow-x-auto">
            {(["home", "local", "public", "notifications", "search"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFeedType(tab)}
                className={`px-3 py-1.5 rounded-lg capitalize transition-all duration-200 flex items-center gap-1 shrink-0 ${
                  feedType === tab
                    ? "bg-primary text-primary-foreground shadow-md font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
                }`}
              >
                {tab === "search" ? (
                  <>
                    <Search className="h-3 w-3" />
                    <span>Buscar</span>
                  </>
                ) : (
                  tab
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Formulario de Conexión de Cuenta */}
        {showAddAccount && (
          <form onSubmit={handleAddAccount} className="bg-secondary/35 border border-border/30 rounded-2xl p-4 space-y-3 transition-all duration-300">
            <h3 className="text-sm font-semibold text-foreground">Conectar con el Fediverso</h3>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="text"
                placeholder="mastodon.social"
                value={instanceInput}
                onChange={(e) => setInstanceInput(e.target.value)}
                className="flex-1 bg-background/50 border border-border/40 rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder-muted-foreground"
              />
              <button
                type="submit"
                disabled={registeringInstance}
                className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium text-sm px-4 py-2 rounded-xl transition-all duration-300 flex items-center justify-center gap-2"
              >
                {registeringInstance ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Globe className="h-4 w-4" />
                    <span>Conectar</span>
                  </>
                )}
              </button>
            </div>
            <p className="text-[11px] text-muted-foreground">
              Esto te redirigirá a tu instancia de Mastodon para autorizar a KognitoAI.
            </p>
          </form>
        )}

        {/* Search View / Timelines Feed */}
        {feedType === "search" ? (
          <div className="flex-1 flex flex-col space-y-4 overflow-hidden">
            {/* Formulario de Búsqueda de Cuentas */}
            <form onSubmit={handleSearchAccounts} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Buscar cuenta (@usuario@instancia.social o nombre)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-background/50 border border-border/40 rounded-xl pl-9 pr-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder-muted-foreground"
                />
              </div>
              <button
                type="submit"
                disabled={loadingSearch || !searchQuery.trim() || !activeAccount}
                className="bg-primary hover:bg-primary/90 text-primary-foreground font-medium text-sm px-4 py-2 rounded-xl transition-all duration-300 flex items-center justify-center gap-1.5 shrink-0"
              >
                {loadingSearch ? <Loader2 className="h-4 w-4 animate-spin" /> : "Buscar"}
              </button>
            </form>

            {/* Resultados de Búsqueda */}
            <div className="flex-1 overflow-y-auto max-h-[440px] pr-2 space-y-3 custom-scrollbar">
              {loadingSearch ? (
                <div className="flex flex-col items-center justify-center py-16 space-y-2 text-muted-foreground">
                  <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  <span className="text-sm">Buscando cuentas...</span>
                </div>
              ) : searchResults.length > 0 ? (
                searchResults.map((acc) => (
                  <div
                    key={acc.id}
                    className="bg-card/40 border border-border/30 hover:border-primary/20 hover:bg-card/60 transition-all duration-300 rounded-xl p-4 space-y-3 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-center space-x-3">
                        <img
                          src={acc.avatar}
                          alt={acc.username}
                          className="h-11 w-11 rounded-full border border-border/20 object-cover"
                        />
                        <div>
                          <h4 className="text-sm font-semibold text-foreground leading-tight">
                            {acc.display_name || acc.username}
                          </h4>
                          <p className="text-xs text-muted-foreground">@{acc.acct}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleToggleFollow(acc.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all duration-200 ${
                          followingMap[acc.id]
                            ? "bg-secondary/60 text-foreground border border-border/40 hover:bg-rose-500/20 hover:text-rose-500"
                            : "bg-primary text-primary-foreground hover:bg-primary/90 shadow-md"
                        }`}
                      >
                        {followingMap[acc.id] ? (
                          <>
                            <UserCheck className="h-3.5 w-3.5" />
                            <span>Siguiendo</span>
                          </>
                        ) : (
                          <>
                            <UserPlus className="h-3.5 w-3.5" />
                            <span>Seguir</span>
                          </>
                        )}
                      </button>
                    </div>

                    {acc.note && (
                      <div
                        className="text-xs text-foreground/80 leading-relaxed line-clamp-3 bg-secondary/15 rounded-lg p-2 border border-border/10"
                        dangerouslySetInnerHTML={{ __html: sanitizeFediverseHtml(acc.note) }}
                      />
                    )}

                    <div className="flex items-center space-x-4 text-[11px] text-muted-foreground pt-1 border-t border-border/10">
                      <span><strong>{acc.statuses_count}</strong> posts</span>
                      <span><strong>{acc.following_count}</strong> siguiendo</span>
                      <span><strong>{acc.followers_count}</strong> seguidores</span>
                      {acc.url && (
                        <a
                          href={acc.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-auto text-primary hover:underline flex items-center gap-1"
                        >
                          <Globe className="h-3 w-3" /> Ver perfil
                        </a>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border/30 rounded-2xl">
                  <User className="h-8 w-8 mb-2 opacity-40" />
                  <p className="text-sm">Ingresa un usuario o handle para buscar.</p>
                  <p className="text-xs opacity-75">Ejemplo: @usuario@instancia.social o nombre de cuenta.</p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto max-h-[500px] pr-2 space-y-4 custom-scrollbar">
            {loadingFeed ? (
              <div className="flex flex-col items-center justify-center py-16 space-y-2 text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
                <span className="text-sm">Cargando publicaciones...</span>
              </div>
            ) : feed.length > 0 ? (
              feed.map((rawItem: any) => {
                // Support both standard statuses and notification items
                const toot: Toot = rawItem.status || rawItem;
                const isReblog = !!toot.reblog;
                const effectiveToot = toot.reblog || toot;
                const isSensitive = effectiveToot.sensitive && !revealedSensitive[effectiveToot.id];

                return (
                  <div
                    key={rawItem.id || toot.id}
                    className="bg-card/40 border border-border/30 hover:border-primary/20 hover:bg-card/60 transition-all duration-300 rounded-2xl p-4 space-y-3 group shadow-sm hover:shadow-md"
                  >
                    {/* Reblog Header */}
                    {isReblog && (
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-medium pb-1 border-b border-border/10">
                        <Repeat className="h-3.5 w-3.5 text-emerald-500" />
                        <span><strong>{toot.account.display_name || toot.account.username}</strong> compartió</span>
                      </div>
                    )}

                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <img
                          src={effectiveToot.account.avatar}
                          alt={effectiveToot.account.username}
                          className="h-10 w-10 rounded-full border border-border/20 object-cover"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                        <div>
                          <h4 className="text-sm font-semibold text-foreground leading-tight">
                            {effectiveToot.account.display_name || effectiveToot.account.username}
                          </h4>
                          <p className="text-xs text-muted-foreground">
                            @{effectiveToot.account.acct}
                          </p>
                        </div>
                      </div>
                      <span className="text-[11px] text-muted-foreground">
                        {new Date(effectiveToot.created_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit"
                        })}
                      </span>
                    </div>

                    {/* Content Warning / Spoiler */}
                    {effectiveToot.spoiler_text ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-2.5 rounded-xl bg-secondary/30 text-xs border border-border/20">
                          <span className="font-medium text-foreground">{effectiveToot.spoiler_text}</span>
                          <button
                            onClick={() =>
                              setExpandedSpoilers((prev) => ({
                                ...prev,
                                [effectiveToot.id]: !prev[effectiveToot.id]
                              }))
                            }
                            className="text-xs text-primary font-semibold hover:underline"
                          >
                            {expandedSpoilers[effectiveToot.id] ? "Ocultar" : "Mostrar más"}
                          </button>
                        </div>
                        {expandedSpoilers[effectiveToot.id] && (
                          <div
                            className="text-sm text-foreground/90 leading-relaxed break-words px-1"
                            dangerouslySetInnerHTML={{ __html: sanitizeFediverseHtml(effectiveToot.content) }}
                          />
                        )}
                      </div>
                    ) : (
                      <div
                        className="text-sm text-foreground/90 leading-relaxed break-words px-1"
                        dangerouslySetInnerHTML={{ __html: sanitizeFediverseHtml(effectiveToot.content) }}
                      />
                    )}

                    {/* Media Attachments */}
                    {effectiveToot.media_attachments && effectiveToot.media_attachments.length > 0 && (
                      isSensitive ? (
                        <div className="rounded-xl overflow-hidden bg-secondary/30 border border-border/30 p-6 flex flex-col items-center justify-center gap-2 text-center my-2">
                          <EyeOff className="h-6 w-6 text-muted-foreground" />
                          <p className="text-xs text-muted-foreground font-medium">Contenido marcado como sensible</p>
                          <button
                            onClick={() =>
                              setRevealedSensitive((prev) => ({ ...prev, [effectiveToot.id]: true }))
                            }
                            className="text-xs bg-primary/20 text-primary hover:bg-primary/30 border border-primary/30 px-3 py-1.5 rounded-xl transition-colors font-medium flex items-center gap-1.5 mt-1"
                          >
                            <Eye className="h-3.5 w-3.5" /> Mostrar contenido
                          </button>
                        </div>
                      ) : (
                        <div
                          className={`mt-2 rounded-xl overflow-hidden gap-2 ${
                            effectiveToot.media_attachments.length === 1
                              ? "grid grid-cols-1"
                              : "grid grid-cols-2"
                          }`}
                        >
                          {effectiveToot.media_attachments.map((media, idx) => (
                            <div
                              key={media.id || idx}
                              className={`relative group/media overflow-hidden rounded-xl bg-black/20 border border-border/20 flex items-center justify-center ${
                                effectiveToot.media_attachments?.length === 3 && idx === 0
                                  ? "col-span-2 max-h-80"
                                  : "max-h-64"
                              }`}
                            >
                              {media.type === "video" ? (
                                <video
                                  src={media.url}
                                  controls
                                  className="w-full max-h-72 object-cover rounded-xl"
                                />
                              ) : media.type === "gifv" ? (
                                <video
                                  src={media.url}
                                  autoPlay
                                  loop
                                  muted
                                  playsInline
                                  className="w-full max-h-72 object-cover rounded-xl"
                                />
                              ) : media.type === "audio" ? (
                                <audio src={media.url} controls className="w-full p-2" />
                              ) : (
                                <div
                                  onClick={() =>
                                    setSelectedMedia({
                                      url: media.url || media.preview_url,
                                      alt: media.description || ""
                                    })
                                  }
                                  className="relative cursor-pointer w-full h-full min-h-[140px] flex items-center justify-center overflow-hidden"
                                >
                                  <img
                                    src={media.preview_url || media.url}
                                    alt={media.description || "Imagen del post"}
                                    className="w-full h-full object-cover max-h-72 hover:scale-[1.02] transition-transform duration-300 rounded-xl"
                                    loading="lazy"
                                  />
                                  <div className="absolute inset-0 bg-black/0 group-hover/media:bg-black/25 transition-colors flex items-center justify-center opacity-0 group-hover/media:opacity-100">
                                    <div className="p-2 rounded-full bg-black/60 text-white backdrop-blur-sm shadow-lg">
                                      <Maximize2 className="h-4 w-4" />
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )
                    )}

                    {/* Link Card Preview (if no media attachments) */}
                    {(!effectiveToot.media_attachments || effectiveToot.media_attachments.length === 0) &&
                      effectiveToot.card &&
                      effectiveToot.card.url && (
                        <a
                          href={effectiveToot.card.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-2 flex flex-col sm:flex-row overflow-hidden rounded-xl border border-border/30 bg-secondary/15 hover:bg-secondary/30 transition-all group/card"
                        >
                          {effectiveToot.card.image && (
                            <img
                              src={effectiveToot.card.image}
                              alt={effectiveToot.card.title}
                              className="h-32 sm:w-36 sm:h-auto object-cover shrink-0"
                              loading="lazy"
                            />
                          )}
                          <div className="p-3 flex flex-col justify-center space-y-1 overflow-hidden">
                            <span className="text-[11px] text-muted-foreground flex items-center gap-1 font-medium">
                              <ExternalLink className="h-3 w-3 text-primary" />{" "}
                              {effectiveToot.card.provider_name || "Enlace externo"}
                            </span>
                            <h5 className="text-xs font-semibold text-foreground line-clamp-1 group-hover/card:text-primary transition-colors">
                              {effectiveToot.card.title}
                            </h5>
                            {effectiveToot.card.description && (
                              <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                                {effectiveToot.card.description}
                              </p>
                            )}
                          </div>
                        </a>
                      )}

                    {/* Footer / Actions */}
                    <div className="flex items-center justify-between pt-2 border-t border-border/10 text-xs text-muted-foreground">
                      <div className="flex items-center space-x-4">
                        <button
                          onClick={() => {
                            setInReplyTo(effectiveToot);
                            setTootText(`@${effectiveToot.account.acct} `);
                          }}
                          className="flex items-center space-x-1 hover:text-primary transition-colors duration-200"
                        >
                          <MessageSquare className="h-4 w-4" />
                          <span>{effectiveToot.replies_count || 0}</span>
                        </button>
                        <button className="flex items-center space-x-1 hover:text-emerald-500 transition-colors duration-200">
                          <Repeat className="h-4 w-4" />
                          <span>{effectiveToot.reblogs_count || 0}</span>
                        </button>
                        <button className="flex items-center space-x-1 hover:text-rose-500 transition-colors duration-200">
                          <Heart className="h-4 w-4" />
                          <span>{effectiveToot.favourites_count || 0}</span>
                        </button>
                      </div>

                      <button
                        onClick={() => handleSummarizeThread(effectiveToot.id)}
                        className="flex items-center space-x-1 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 px-2 py-1 rounded-lg transition-all duration-200"
                      >
                        {summaryLoading && activeSummary === effectiveToot.id ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Sparkles className="h-3.5 w-3.5" />
                        )}
                        <span className="text-[11px] font-medium">Resumir Hilo</span>
                      </button>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border/30 rounded-2xl">
                <Share2 className="h-8 w-8 mb-2 opacity-40" />
                <p className="text-sm">No hay publicaciones disponibles.</p>
                <p className="text-xs opacity-75">Conecta una cuenta o cambia de feed.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* AI Copilot & Editor Panel (Right Side) */}
      <div className="lg:col-span-5 flex flex-col space-y-4 bg-card/30 backdrop-blur-md border border-border/40 rounded-2xl p-6 shadow-xl">
        
        {/* Editor de Toots */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-md font-bold text-foreground">Redactar Publicación</h3>
            {inReplyTo && (
              <button
                onClick={() => {
                  setInReplyTo(null);
                  setTootText("");
                }}
                className="text-xs text-rose-500 hover:underline flex items-center space-x-1"
              >
                <ArrowLeft className="h-3 w-3" />
                <span>Cancelar respuesta</span>
              </button>
            )}
          </div>

          {inReplyTo && (
            <div className="bg-secondary/25 border border-border/20 rounded-xl p-3 text-xs text-muted-foreground">
              Respondiendo a <strong>@{inReplyTo.account.acct}</strong>:
              <div className="line-clamp-2 mt-1" dangerouslySetInnerHTML={{ __html: sanitizeFediverseHtml(inReplyTo.content) }} />
            </div>
          )}

          <div className="relative">
            <textarea
              className="w-full min-h-[120px] bg-background/50 border border-border/40 focus:border-primary rounded-xl p-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder-muted-foreground resize-none"
              placeholder="¿Qué está pasando en el Fediverso? (Límite: 500 caracteres)"
              value={tootText}
              onChange={(e) => setTootText(e.target.value.slice(0, 500))}
            />
            <div className="absolute bottom-3 right-3 text-xs text-muted-foreground font-mono">
              {tootText.length}/500
            </div>
          </div>

          <div className="flex justify-between items-center gap-2">
            <button
              onClick={handleAiImprove}
              disabled={aiLoading || !tootText.trim()}
              className="bg-secondary/40 hover:bg-secondary/60 text-foreground font-medium text-xs px-3 py-2 rounded-xl transition-all duration-300 flex items-center space-x-1 border border-border/20"
            >
              <Sparkles className="h-3.5 w-3.5 text-primary" />
              <span>Optimizar Tono</span>
            </button>
            
            <button
              onClick={handlePublishToot}
              disabled={!tootText.trim() || !activeAccount}
              className="bg-primary hover:bg-primary/95 text-primary-foreground font-semibold text-sm px-4 py-2 rounded-xl transition-all duration-300 flex items-center space-x-1.5 shadow-lg"
            >
              <Send className="h-4 w-4" />
              <span>Publicar Toot</span>
            </button>
          </div>
        </div>

        {/* Copilot AI Workspace */}
        <div className="flex-1 flex flex-col space-y-3 border-t border-border/20 pt-4">
          <h3 className="text-md font-bold text-foreground flex items-center space-x-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <span>Copiloto de IA</span>
          </h3>

          {/* Generador de Borradores */}
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">Instrucciones para generar un nuevo borrador:</label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Escribe sobre un nuevo artículo de inteligencia artificial..."
                value={aiPrompt}
                onChange={(e) => setAiPrompt(e.target.value)}
                className="flex-1 bg-background/50 border border-border/40 rounded-xl px-3 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder-muted-foreground"
              />
              <button
                onClick={handleAiCompose}
                disabled={aiLoading || !aiPrompt.trim()}
                className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 text-xs px-3 py-2 rounded-xl font-semibold transition-all duration-300"
              >
                {aiLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "Crear"}
              </button>
            </div>
          </div>

          {/* Resultados de la IA (Resúmenes, etc.) */}
          <div className="flex-1 flex flex-col space-y-2">
            <span className="text-xs text-muted-foreground">Resultados del análisis / Resúmenes:</span>
            <div className="flex-1 bg-background/35 border border-border/20 rounded-xl p-4 overflow-y-auto text-xs leading-relaxed text-foreground/90 max-h-[220px]">
              {aiResult ? (
                <div className="space-y-2 whitespace-pre-wrap">{aiResult}</div>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground opacity-60">
                  <FileText className="h-8 w-8 mr-2" />
                  <span>Aquí verás el resumen de los hilos de discusión del fediverso.</span>
                </div>
              )}
            </div>
            {aiResult && (
              <button
                onClick={() => setAiResult("")}
                className="text-xs text-muted-foreground hover:text-foreground hover:underline self-end"
              >
                Limpiar consola
              </button>
            )}
          </div>

        </div>

      </div>

      {/* Lightbox Modal para vista previa de imágenes */}
      {selectedMedia && (
        <div
          className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setSelectedMedia(null)}
        >
          <div
            className="relative max-w-5xl max-h-[90vh] flex flex-col items-center justify-center"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setSelectedMedia(null)}
              className="absolute -top-10 right-0 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white transition-colors"
              title="Cerrar"
            >
              <X className="h-5 w-5" />
            </button>
            <img
              src={selectedMedia.url}
              alt={selectedMedia.alt || "Imagen completa"}
              className="max-h-[80vh] max-w-full rounded-2xl shadow-2xl object-contain"
            />
            {selectedMedia.alt && (
              <p className="text-xs text-white/90 bg-black/60 px-4 py-2 rounded-xl mt-3 max-w-2xl text-center backdrop-blur-sm">
                {selectedMedia.alt}
              </p>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
