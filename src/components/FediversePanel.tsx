import React, { useState, useEffect, useRef } from "react";
import {
  Share2, Globe, Home, Bell, User, Plus, Loader2, Sparkles,
  Check, Send, FileText, MessageSquare, Heart, Repeat, ArrowLeft
} from "lucide-react";

interface FediversoAccount {
  id: string;
  instance_url: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
}

interface Toot {
  id: string;
  created_at: string;
  content: string;
  account: {
    username: string;
    acct: string;
    display_name: string;
    avatar: string;
  };
  reblogs_count: number;
  favourites_count: number;
  replies_count: number;
}

export function FediversePanel() {
  const [accounts, setAccounts] = useState<FediversoAccount[]>([]);
  const [activeAccount, setActiveAccount] = useState<FediversoAccount | null>(null);
  const [feed, setFeed] = useState<Toot[]>([]);
  const [feedType, setFeedType] = useState<"home" | "local" | "public" | "notifications">("home");
  const [loadingFeed, setLoadingFeed] = useState(false);
  const [loadingAccounts, setLoadingAccounts] = useState(true);
  
  // Registering instance state
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [instanceInput, setInstanceInput] = useState("");
  const [registeringInstance, setRegisteringInstance] = useState(false);

  // Editor and AI state
  const [tootText, setTootText] = useState("");
  const [inReplyTo, setInReplyTo] = useState<Toot | null>(null);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [activeSummary, setActiveSummary] = useState<string | null>(null);

  // Check URL parameters for OAuth Callback on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");
    const client_id = urlParams.get("client_id");
    const instance_url = urlParams.get("instance_url");

    if (code && client_id && instance_url) {
      handleOAuthCallback(code, client_id, instance_url);
    } else {
      fetchAccounts();
    }
  }, []);

  // Fetch feed when active account or feed type changes
  useEffect(() => {
    if (activeAccount) {
      fetchFeed(activeAccount.id, feedType);
    } else {
      setFeed([]);
    }
  }, [activeAccount, feedType]);

  const fetchAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const resp = await fetch("/api/fediverso/accounts");
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
    try {
      const resp = await fetch("/api/fediverso/callback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, client_id, instance_url })
      });
      if (resp.ok) {
        // Clean URL params
        window.history.replaceState({}, document.title, window.location.pathname);
        await fetchAccounts();
      } else {
        const errData = await resp.json();
        alert(`Error al conectar cuenta: ${errData.detail || "Fallo desconocido"}`);
      }
    } catch (err) {
      console.error("Error handling OAuth callback:", err);
    }
  };

  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!instanceInput.trim()) return;

    setRegisteringInstance(true);
    try {
      const resp = await fetch("/api/fediverso/register-instance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instance_url: instanceInput })
      });

      if (resp.ok) {
        const data = await resp.json();
        // Redirect user to instance OAuth authorize page, passing instance and client_id so we get it back
        const returnUrl = `${data.authorize_url}&state=${encodeURIComponent(
          JSON.stringify({ instance: data.instance_url, client_id: data.client_id })
        )}`;
        
        // Save temporary client details in localStorage to verify on callback
        localStorage.setItem("fediverso_temp_instance", data.instance_url);
        localStorage.setItem("fediverso_temp_client_id", data.client_id);
        
        // Append client_id and instance_url directly to redirect URI by dynamically changing location
        const oauthUrl = data.authorize_url.replace(
          "redirect_uri=http://localhost:3000/fediverso",
          `redirect_uri=http://localhost:3000/fediverso?instance_url=${encodeURIComponent(
            data.instance_url
          )}%26client_id=${encodeURIComponent(data.client_id)}`
        );
        window.location.href = oauthUrl;
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
      const resp = await fetch(`/api/fediverso/feed?account_id=${accountId}&feed_type=${type}`);
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

  const handlePublishToot = async () => {
    if (!activeAccount || !tootText.trim()) return;

    try {
      const resp = await fetch("/api/fediverso/toot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
        headers: { "Content-Type": "application/json" },
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
        headers: { "Content-Type": "application/json" },
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
        headers: { "Content-Type": "application/json" },
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
          <div className="flex bg-secondary/20 border border-border/20 rounded-xl p-1 text-xs">
            {(["home", "local", "public", "notifications"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFeedType(tab)}
                className={`px-3 py-1.5 rounded-lg capitalize transition-all duration-200 ${
                  feedType === tab
                    ? "bg-primary text-primary-foreground shadow-md font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
                }`}
              >
                {tab}
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

        {/* Timelines Feed */}
        <div className="flex-1 overflow-y-auto max-h-[500px] pr-2 space-y-4 custom-scrollbar">
          {loadingFeed ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-2 text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <span className="text-sm">Cargando publicaciones...</span>
            </div>
          ) : feed.length > 0 ? (
            feed.map((toot) => (
              <div
                key={toot.id}
                className="bg-card/40 border border-border/30 hover:border-primary/20 hover:bg-card/60 transition-all duration-300 rounded-xl p-4 space-y-3 group shadow-sm hover:shadow-md"
              >
                {/* Header */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <img
                      src={toot.account.avatar}
                      alt={toot.account.username}
                      className="h-10 w-10 rounded-full border border-border/20 object-cover"
                    />
                    <div>
                      <h4 className="text-sm font-semibold text-foreground leading-tight">
                        {toot.account.display_name || toot.account.username}
                      </h4>
                      <p className="text-xs text-muted-foreground">
                        @{toot.account.acct}
                      </p>
                    </div>
                  </div>
                  <span className="text-[11px] text-muted-foreground">
                    {new Date(toot.created_at).toLocaleDateString()}
                  </span>
                </div>

                {/* Content */}
                <div
                  className="text-sm text-foreground/90 leading-relaxed break-words px-1"
                  dangerouslySetInnerHTML={{ __html: toot.content }}
                />

                {/* Footer / Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-border/10 text-xs text-muted-foreground">
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={() => {
                        setInReplyTo(toot);
                        setTootText(`@${toot.account.acct} `);
                      }}
                      className="flex items-center space-x-1 hover:text-primary transition-colors duration-200"
                    >
                      <MessageSquare className="h-4 w-4" />
                      <span>{toot.replies_count}</span>
                    </button>
                    <button className="flex items-center space-x-1 hover:text-emerald-500 transition-colors duration-200">
                      <Repeat className="h-4 w-4" />
                      <span>{toot.reblogs_count}</span>
                    </button>
                    <button className="flex items-center space-x-1 hover:text-rose-500 transition-colors duration-200">
                      <Heart className="h-4 w-4" />
                      <span>{toot.favourites_count}</span>
                    </button>
                  </div>

                  <button
                    onClick={() => handleSummarizeThread(toot.id)}
                    className="flex items-center space-x-1 bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 px-2 py-1 rounded-lg transition-all duration-200"
                  >
                    {summaryLoading && activeSummary === toot.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                    <span className="text-[11px] font-medium">Resumir Hilo</span>
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground border border-dashed border-border/30 rounded-2xl">
              <Share2 className="h-8 w-8 mb-2 opacity-40" />
              <p className="text-sm">No hay publicaciones disponibles.</p>
              <p className="text-xs opacity-75">Conecta una cuenta o cambia de feed.</p>
            </div>
          )}
        </div>
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
              <div className="line-clamp-2 mt-1" dangerouslySetInnerHTML={{ __html: inReplyTo.content }} />
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

    </div>
  );
}
