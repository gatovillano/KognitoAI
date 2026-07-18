import React, { useState, useEffect, useRef } from "react";
import {
  Share2, Globe, Home, Bell, User, Plus, Loader2, Sparkles,
  Check, Send, FileText, MessageSquare, Heart, Repeat, ArrowLeft,
  Image, X, Upload, EyeOff, Eye, ShieldAlert, Hash
} from "lucide-react";

interface FediversoAccount {
  id: string;
  instance_url: string;
  username: string;
  display_name: string | null;
  avatar_url: string | null;
}

interface MediaAttachment {
  id: string;
  type: 'image' | 'video' | 'gifv' | 'audio' | 'unknown';
  url: string;
  preview_url: string | null;
  description: string | null;
}

interface Toot {
  id: string;
  created_at: string;
  content: string;
  account: {
    id: string;
    username: string;
    acct: string;
    display_name: string;
    avatar: string;
    header?: string;
    note?: string;
  };
  reblogs_count: number;
  favourites_count: number;
  replies_count: number;
  favourited?: boolean;
  reblogged?: boolean;
  media_attachments: MediaAttachment[];
}

interface MastodonProfile {
  id: string;
  username: string;
  acct: string;
  display_name: string;
  avatar: string;
  header: string;
  note: string;
  url: string;
  followers_count: number;
  following_count: number;
  statuses_count: number;
}

export function FediversePanel() {
  const [accounts, setAccounts] = useState<FediversoAccount[]>([]);
  const [activeAccount, setActiveAccount] = useState<FediversoAccount | null>(null);
  const [feed, setFeed] = useState<Toot[]>([]);
  const [feedType, setFeedType] = useState<"home" | "local" | "public" | "notifications" | "hashtag">("home");
  const [activeHashtag, setActiveHashtag] = useState<string>("fediverse");
  const [hashtagInput, setHashtagInput] = useState<string>("");
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

  // Media upload state
  const [pendingMedia, setPendingMedia] = useState<Array<{ file: File; preview: string; id?: string; uploading: boolean }>>([])
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Content Warning / NSFW state
  const [showCW, setShowCW] = useState(false);
  const [cwText, setCwText] = useState("");
  const [isNSFW, setIsNSFW] = useState(false);

  // Lightbox state
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  // Account to publish from (independent from feed account)
  const [publishAccount, setPublishAccount] = useState<FediversoAccount | null>(null);

  // Profile Modal State
  const [selectedProfile, setSelectedProfile] = useState<MastodonProfile | null>(null);
  const [profileRelationship, setProfileRelationship] = useState<{ following: boolean } | null>(null);
  const [profileToots, setProfileToots] = useState<Toot[]>([]);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [followLoading, setFollowLoading] = useState(false);

  // Check URL parameters for OAuth Callback on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");
    const stateStr = urlParams.get("state");

    let client_id = null;
    let instance_url = null;

    if (stateStr) {
      try {
        const decoded = decodeURIComponent(stateStr);
        const stateData = JSON.parse(decoded);
        client_id = stateData.client_id;
        instance_url = stateData.instance;
      } catch (err) {
        console.error("Error parsing state parameter:", err);
      }
    }

    // Fallbacks
    if (!client_id) {
      client_id = urlParams.get("client_id") || (typeof window !== 'undefined' ? localStorage.getItem("fediverso_temp_client_id") : null);
    }
    if (!instance_url) {
      instance_url = urlParams.get("instance_url") || (typeof window !== 'undefined' ? localStorage.getItem("fediverso_temp_instance") : null);
    }

    if (code && client_id && instance_url) {
      handleOAuthCallback(code, client_id, instance_url);
    } else {
      fetchAccounts();
    }
  }, []);

  // Fetch feed when active account, feed type, or hashtag changes
  useEffect(() => {
    if (activeAccount) {
      fetchFeed(activeAccount.id, feedType, activeHashtag);
    } else {
      setFeed([]);
    }
  }, [activeAccount, feedType, activeHashtag]);

  const fetchAccounts = async () => {
    setLoadingAccounts(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const resp = await fetch("/api/fediverso/accounts", { headers });
      if (resp.ok) {
        const data = await resp.json();
        setAccounts(data);
        if (data.length > 0 && !activeAccount) {
          setActiveAccount(data[0]);
          setPublishAccount(data[0]);
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
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const resp = await fetch("/api/fediverso/callback", {
        method: "POST",
        headers,
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
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const resp = await fetch("/api/fediverso/register-instance", {
        method: "POST",
        headers,
        body: JSON.stringify({ instance_url: instanceInput })
      });

      if (resp.ok) {
        const data = await resp.json();
        
        // Save temporary client details in localStorage to verify on callback
        localStorage.setItem("fediverso_temp_instance", data.instance_url);
        localStorage.setItem("fediverso_temp_client_id", data.client_id);
        
        // Use standard state parameter instead of hacking redirect_uri query parameters
        const statePayload = JSON.stringify({ instance: data.instance_url, client_id: data.client_id });
        const oauthUrl = `${data.authorize_url}&state=${encodeURIComponent(statePayload)}`;
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

  const fetchFeed = async (accountId: string, type: string, tag?: string) => {
    setLoadingFeed(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;
      let url = `/api/fediverso/feed?account_id=${accountId}&feed_type=${type}`;
      if (type === "hashtag") {
        const cleanTag = (tag || activeHashtag || "fediverse").trim().replace(/^#/, "");
        url += `&hashtag=${encodeURIComponent(cleanTag)}`;
      }
      const resp = await fetch(url, { headers });
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

  const handleContentClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement;
    const hashtagLink = target.closest("a.hashtag") || target.closest("a[href*='/tags/']");
    if (hashtagLink) {
      e.preventDefault();
      const text = hashtagLink.textContent || "";
      const tagMatch = text.match(/#([\w\d_-]+)/);
      if (tagMatch && tagMatch[1]) {
        const tag = tagMatch[1];
        setActiveHashtag(tag);
        setHashtagInput(tag);
        setFeedType("hashtag");
      }
    }
  };

  const handlePublishToot = async () => {
    if (!publishAccount || !tootText.trim()) return;

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      // Collect uploaded media IDs
      const media_ids = pendingMedia.filter(m => m.id).map(m => m.id!);

      const resp = await fetch("/api/fediverso/toot", {
        method: "POST",
        headers,
        body: JSON.stringify({
          account_id: publishAccount.id,
          status: tootText,
          in_reply_to_id: inReplyTo?.id || null,
          media_ids: media_ids.length > 0 ? media_ids : null,
          spoiler_text: showCW && cwText.trim() ? cwText.trim() : null,
          sensitive: isNSFW ? true : null
        })
      });

      if (resp.ok) {
        setTootText("");
        setInReplyTo(null);
        setPendingMedia([]);
        setCwText("");
        setShowCW(false);
        setIsNSFW(false);
        if (activeAccount) fetchFeed(activeAccount.id, feedType);
      } else {
        alert("Fallo al publicar el toot.");
      }
    } catch (err) {
      console.error("Error publishing toot:", err);
    }
  };

  const handleMediaSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!activeAccount || !e.target.files) return;
    const files = Array.from(e.target.files).slice(0, 4 - pendingMedia.length); // max 4
    const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;

    for (const file of files) {
      const preview = URL.createObjectURL(file);
      const item = { file, preview, uploading: true };
      setPendingMedia(prev => [...prev, item]);

      try {
        const formData = new FormData();
        formData.append("account_id", publishAccount!.id);
        formData.append("file", file);

        const headers: any = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;

        const resp = await fetch("/api/fediverso/media/upload", {
          method: "POST",
          headers,
          body: formData,
        });

        if (resp.ok) {
          const data = await resp.json();
          setPendingMedia(prev =>
            prev.map(m => m.preview === preview ? { ...m, id: data.id, uploading: false } : m)
          );
        } else {
          setPendingMedia(prev => prev.filter(m => m.preview !== preview));
          alert("Error al subir imagen.");
        }
      } catch {
        setPendingMedia(prev => prev.filter(m => m.preview !== preview));
      }
    }
    // Reset input so same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleAiCompose = async () => {
    if (!aiPrompt.trim()) return;

    setAiLoading(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const resp = await fetch("/api/fediverso/ai/compose", {
        method: "POST",
        headers,
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
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const resp = await fetch("/api/fediverso/ai/compose", {
        method: "POST",
        headers,
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
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const resp = await fetch("/api/fediverso/ai/summarize-thread", {
        method: "POST",
        headers,
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

  const handleToggleFavourite = async (toot: Toot) => {
    if (!activeAccount) return;
    const isFav = toot.favourited;
    const endpoint = isFav ? "/api/fediverso/toot/unfavourite" : "/api/fediverso/toot/favourite";
    
    // Optimistic update
    setFeed(prev => prev.map(t => {
      if (t.id === toot.id) {
        return {
          ...t,
          favourited: !isFav,
          favourites_count: isFav ? Math.max(0, t.favourites_count - 1) : t.favourites_count + 1
        };
      }
      return t;
    }));

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({
          account_id: activeAccount.id,
          status_id: toot.id
        })
      });
    } catch (err) {
      console.error("Error toggling favourite:", err);
    }
  };

  const handleToggleReblog = async (toot: Toot) => {
    if (!activeAccount) return;
    const isReblogged = toot.reblogged;
    const endpoint = isReblogged ? "/api/fediverso/toot/unreblog" : "/api/fediverso/toot/reblog";

    // Optimistic update
    setFeed(prev => prev.map(t => {
      if (t.id === toot.id) {
        return {
          ...t,
          reblogged: !isReblogged,
          reblogs_count: isReblogged ? Math.max(0, t.reblogs_count - 1) : t.reblogs_count + 1
        };
      }
      return t;
    }));

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({
          account_id: activeAccount.id,
          status_id: toot.id
        })
      });
    } catch (err) {
      console.error("Error toggling reblog:", err);
    }
  };

  const handleOpenProfile = async (targetAccountId: string) => {
    if (!activeAccount) return;
    setLoadingProfile(true);
    setSelectedProfile(null);
    setProfileRelationship(null);
    setProfileToots([]);

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [profResp, relResp, statusesResp] = await Promise.all([
        fetch(`/api/fediverso/account/profile?account_id=${activeAccount.id}&target_account_id=${targetAccountId}`, { headers }),
        fetch(`/api/fediverso/account/relationship?account_id=${activeAccount.id}&target_account_id=${targetAccountId}`, { headers }),
        fetch(`/api/fediverso/account/statuses?account_id=${activeAccount.id}&target_account_id=${targetAccountId}`, { headers })
      ]);

      if (profResp.ok) {
        const profData = await profResp.json();
        setSelectedProfile(profData);
      }
      if (relResp.ok) {
        const relData = await relResp.json();
        setProfileRelationship({ following: !!relData.following });
      }
      if (statusesResp.ok) {
        const statusesData = await statusesResp.json();
        setProfileToots(statusesData);
      }
    } catch (err) {
      console.error("Error loading profile:", err);
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleToggleFollow = async () => {
    if (!activeAccount || !selectedProfile || !profileRelationship) return;
    const isFollowing = profileRelationship.following;
    const endpoint = isFollowing ? "/api/fediverso/account/unfollow" : "/api/fediverso/account/follow";

    setFollowLoading(true);
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem("authToken") : null;
      const headers: any = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const resp = await fetch(endpoint, {
        method: "POST",
        headers,
        body: JSON.stringify({
          account_id: activeAccount.id,
          target_account_id: selectedProfile.id
        })
      });

      if (resp.ok) {
        const relData = await resp.json();
        setProfileRelationship({ following: !!relData.following });
        setSelectedProfile(prev => prev ? {
          ...prev,
          followers_count: isFollowing ? Math.max(0, prev.followers_count - 1) : prev.followers_count + 1
        } : null);
      }
    } catch (err) {
      console.error("Error toggling follow:", err);
    } finally {
      setFollowLoading(false);
    }
  };


  return (
    <>
    {/* Lightbox */}
    {lightboxUrl && (
      <div
        className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-sm flex items-center justify-center"
        onClick={() => setLightboxUrl(null)}
        onKeyDown={e => e.key === 'Escape' && setLightboxUrl(null)}
        tabIndex={0}
      >
        <button
          className="absolute top-4 right-4 text-white/70 hover:text-white bg-white/10 hover:bg-white/20 rounded-full p-2 transition-colors"
          onClick={() => setLightboxUrl(null)}
        >
          <X className="h-6 w-6" />
        </button>
        <img
          src={lightboxUrl}
          alt="Vista ampliada"
          className="max-w-[92vw] max-h-[92vh] object-contain rounded-xl shadow-2xl"
          onClick={e => e.stopPropagation()}
        />
      </div>
    )}

    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6" style={{ minHeight: 'calc(100vh - 180px)' }}>
      
      {/* Feed Panel (Left Side) */}
      <div className="lg:col-span-7 flex flex-col space-y-4 bg-card/30 backdrop-blur-md border border-border/40 rounded-2xl p-6 shadow-xl overflow-hidden">
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
            {(["home", "local", "public", "notifications", "hashtag"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setFeedType(tab)}
                className={`px-3 py-1.5 rounded-lg capitalize transition-all duration-200 flex items-center space-x-1 whitespace-nowrap ${
                  feedType === tab
                    ? "bg-primary text-primary-foreground shadow-md font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/40"
                }`}
              >
                {tab === "hashtag" ? (
                  <>
                    <Hash className="h-3 w-3" />
                    <span>Hashtag</span>
                  </>
                ) : (
                  <span>{tab}</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Buscador / Selector de Hashtag */}
        {feedType === "hashtag" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (hashtagInput.trim()) {
                const cleaned = hashtagInput.trim().replace(/^#/, "");
                setActiveHashtag(cleaned);
              }
            }}
            className="bg-secondary/35 border border-border/30 rounded-2xl p-3 flex items-center space-x-2 transition-all duration-300"
          >
            <div className="flex items-center space-x-2 flex-1 bg-background/50 border border-border/40 rounded-xl px-3 py-2">
              <Hash className="h-4 w-4 text-primary" />
              <input
                type="text"
                placeholder="Escribe un hashtag (ej: python, ai, fediverse)"
                value={hashtagInput}
                onChange={(e) => setHashtagInput(e.target.value)}
                className="w-full bg-transparent text-sm text-foreground focus:outline-none placeholder-muted-foreground"
              />
            </div>
            <button
              type="submit"
              className="bg-primary hover:bg-primary/90 text-primary-foreground text-xs px-4 py-2.5 rounded-xl font-medium transition-all shadow-sm"
            >
              Buscar
            </button>
          </form>
        )}

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
        <div className="flex-1 overflow-y-auto min-h-0 pr-2 space-y-4 custom-scrollbar">
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
                  <div
                    onClick={() => handleOpenProfile(toot.account.id)}
                    className="flex items-center space-x-3 cursor-pointer group/user"
                  >
                    <img
                      src={toot.account.avatar}
                      alt={toot.account.username}
                      className="h-10 w-10 rounded-full border border-border/20 object-cover group-hover/user:scale-105 transition-transform duration-200"
                    />
                    <div>
                      <h4 className="text-sm font-semibold text-foreground leading-tight group-hover/user:underline">
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
                  onClick={handleContentClick}
                />

                {/* Media attachments */}
                {toot.media_attachments && toot.media_attachments.length > 0 && (
                  <div className="grid gap-2 rounded-lg overflow-hidden mt-3 max-w-full" style={{
                    gridTemplateColumns: toot.media_attachments.length === 1 ? '1fr' : 'repeat(auto-fit, minmax(150px, 1fr))'
                  }}>
                    {toot.media_attachments.map((media: MediaAttachment) => {
                      if (media.type === 'image') {
                        return (
                          <img
                            key={media.id}
                            src={media.preview_url || media.url}
                            alt={media.description || "Adjunto de imagen"}
                            className="w-full max-h-[550px] object-contain rounded-lg border border-border/10 bg-black/10 cursor-zoom-in hover:opacity-90 transition-opacity duration-200"
                            onClick={() => setLightboxUrl(media.url)}
                          />
                        );
                      } else if (media.type === 'video' || media.type === 'gifv') {
                        return (
                          <video
                            key={media.id}
                            src={media.url}
                            controls
                            className="w-full max-h-[300px] object-cover rounded-lg border border-border/10"
                            preload="none"
                          />
                        );
                      } else if (media.type === 'audio') {
                        return (
                          <audio
                            key={media.id}
                            src={media.url}
                            controls
                            className="w-full mt-1"
                            preload="none"
                          />
                        );
                      }
                      return null;
                    })}
                  </div>
                )}

                {/* Footer / Actions */}
                <div className="flex items-center justify-between pt-2 border-t border-border/10 text-xs text-muted-foreground">
                  <div className="flex items-center space-x-4">
                    <button
                      onClick={() => {
                        setInReplyTo(toot);
                        setTootText(`@${toot.account.acct} `);
                      }}
                      title="Responder"
                      className="flex items-center space-x-1 hover:text-primary transition-colors duration-200"
                    >
                      <MessageSquare className="h-4 w-4" />
                      <span>{toot.replies_count}</span>
                    </button>
                    <button
                      onClick={() => handleToggleReblog(toot)}
                      title={toot.reblogged ? "Deshacer retoot" : "Retootear (Boost)"}
                      className={`flex items-center space-x-1 transition-colors duration-200 ${
                        toot.reblogged ? "text-emerald-500 font-semibold" : "hover:text-emerald-500"
                      }`}
                    >
                      <Repeat className={`h-4 w-4 ${toot.reblogged ? "stroke-[2.5]" : ""}`} />
                      <span>{toot.reblogs_count}</span>
                    </button>
                    <button
                      onClick={() => handleToggleFavourite(toot)}
                      title={toot.favourited ? "Deshacer Me Gusta" : "Me Gusta"}
                      className={`flex items-center space-x-1 transition-colors duration-200 ${
                        toot.favourited ? "text-rose-500 font-semibold" : "hover:text-rose-500"
                      }`}
                    >
                      <Heart className={`h-4 w-4 ${toot.favourited ? "fill-rose-500 text-rose-500" : ""}`} />
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
            <div className="flex items-center gap-2">
              {/* Publish account selector */}
              {accounts.length > 1 && (
                <select
                  className="bg-secondary/40 text-xs font-medium border border-border/30 rounded-lg px-2 py-1.5 appearance-none focus:outline-none focus:ring-1 focus:ring-primary text-foreground cursor-pointer"
                  value={publishAccount?.id || ""}
                  onChange={e => {
                    const acc = accounts.find(a => a.id === e.target.value);
                    if (acc) setPublishAccount(acc);
                  }}
                >
                  {accounts.map(acc => (
                    <option key={acc.id} value={acc.id}>
                      @{acc.username} ({acc.instance_url.replace("https://", "")})
                    </option>
                  ))}
                </select>
              )}
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
          </div>

          {inReplyTo && (
            <div className="bg-secondary/25 border border-border/20 rounded-xl p-3 text-xs text-muted-foreground">
              Respondiendo a <strong>@{inReplyTo.account.acct}</strong>:
              <div className="line-clamp-2 mt-1" dangerouslySetInnerHTML={{ __html: inReplyTo.content }} />
            </div>
          )}

          {/* Content Warning input */}
          {showCW && (
            <input
              type="text"
              placeholder="Escribe tu advertencia de contenido (CW)..."
              value={cwText}
              onChange={e => setCwText(e.target.value.slice(0, 150))}
              className="w-full bg-amber-500/10 border border-amber-400/40 focus:border-amber-400 rounded-xl px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-amber-400 placeholder-amber-300/60"
              autoFocus
            />
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

          {/* Media previews */}
          {pendingMedia.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {pendingMedia.map((m, i) => (
                <div key={i} className="relative w-20 h-20 rounded-lg overflow-hidden border border-border/30 bg-secondary/20">
                  <img src={m.preview} alt="adjunto" className="w-full h-full object-cover" />
                  {m.uploading ? (
                    <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                      <Loader2 className="h-5 w-5 text-white animate-spin" />
                    </div>
                  ) : (
                    <button
                      onClick={() => {
                        URL.revokeObjectURL(m.preview);
                        setPendingMedia(prev => prev.filter((_, idx) => idx !== i));
                      }}
                      className="absolute top-1 right-1 bg-black/60 hover:bg-black/80 text-white rounded-full p-0.5 transition-colors"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,video/*,audio/*"
            multiple
            className="hidden"
            onChange={handleMediaSelect}
          />

          <div className="flex justify-between items-center gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={!activeAccount || pendingMedia.length >= 4}
                title={pendingMedia.length >= 4 ? "Máximo 4 archivos" : "Adjuntar imagen o video"}
                className="bg-secondary/40 hover:bg-secondary/60 text-foreground font-medium text-xs px-3 py-2 rounded-xl transition-all duration-300 flex items-center space-x-1 border border-border/20 disabled:opacity-40"
              >
                <Image className="h-3.5 w-3.5 text-primary" />
                <span>Imagen</span>
              </button>
              <button
                onClick={() => { setShowCW(!showCW); if (showCW) setCwText(""); }}
                title={showCW ? "Quitar advertencia de contenido" : "Añadir advertencia de contenido (CW)"}
                className={`font-medium text-xs px-3 py-2 rounded-xl transition-all duration-300 flex items-center space-x-1 border ${
                  showCW
                    ? "bg-amber-500/20 border-amber-400/40 text-amber-400"
                    : "bg-secondary/40 border-border/20 text-foreground hover:bg-secondary/60"
                }`}
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>CW</span>
              </button>
              <button
                onClick={() => setIsNSFW(!isNSFW)}
                title={isNSFW ? "Quitar marca NSFW" : "Marcar como contenido sensible (NSFW)"}
                className={`font-medium text-xs px-3 py-2 rounded-xl transition-all duration-300 flex items-center space-x-1 border ${
                  isNSFW
                    ? "bg-rose-500/20 border-rose-400/40 text-rose-400"
                    : "bg-secondary/40 border-border/20 text-foreground hover:bg-secondary/60"
                }`}
              >
                {isNSFW ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                <span>NSFW</span>
              </button>
              <button
                onClick={handleAiImprove}
                disabled={aiLoading || !tootText.trim()}
                className="bg-secondary/40 hover:bg-secondary/60 text-foreground font-medium text-xs px-3 py-2 rounded-xl transition-all duration-300 flex items-center space-x-1 border border-border/20"
              >
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                <span>Optimizar Tono</span>
              </button>
            </div>
            
            <button
              onClick={handlePublishToot}
              disabled={!tootText.trim() || !publishAccount || pendingMedia.some(m => m.uploading)}
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

    {/* Profile Modal */}
    {(selectedProfile || loadingProfile) && (
      <div
        className="fixed inset-0 z-[90] bg-black/70 backdrop-blur-md flex items-center justify-center p-4"
        onClick={() => setSelectedProfile(null)}
      >
        <div
          className="bg-card border border-border/40 rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col relative"
          onClick={e => e.stopPropagation()}
        >
          <button
            onClick={() => setSelectedProfile(null)}
            className="absolute top-3 right-3 z-10 bg-black/60 text-white rounded-full p-1.5 hover:bg-black/80 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>

          {loadingProfile ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Cargando perfil...</p>
            </div>
          ) : selectedProfile && (
            <div>
              {/* Header Image */}
              <div className="h-32 bg-secondary/30 relative overflow-hidden rounded-t-2xl">
                {selectedProfile.header && (
                  <img src={selectedProfile.header} alt="Header" className="w-full h-full object-cover" />
                )}
              </div>

              {/* Profile Bar */}
              <div className="px-6 pb-4 relative">
                <div className="flex justify-between items-end -mt-10 mb-3">
                  <img
                    src={selectedProfile.avatar}
                    alt={selectedProfile.username}
                    className="w-20 h-20 rounded-full border-4 border-card object-cover bg-background shadow-md"
                  />
                  {profileRelationship && (
                    <button
                      onClick={handleToggleFollow}
                      disabled={followLoading}
                      className={`px-4 py-1.5 rounded-xl font-semibold text-xs transition-all duration-300 shadow-md flex items-center gap-1.5 ${
                        profileRelationship.following
                          ? "bg-secondary hover:bg-rose-500/20 hover:text-rose-500 text-foreground border border-border/40"
                          : "bg-primary hover:bg-primary/90 text-primary-foreground"
                      }`}
                    >
                      {followLoading ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : profileRelationship.following ? (
                        <>
                          <User className="h-3.5 w-3.5" />
                          <span>Siguiendo</span>
                        </>
                      ) : (
                        <>
                          <Plus className="h-3.5 w-3.5" />
                          <span>Seguir</span>
                        </>
                      )}
                    </button>
                  )}
                </div>

                <h3 className="text-lg font-bold text-foreground leading-tight">
                  {selectedProfile.display_name || selectedProfile.username}
                </h3>
                <p className="text-xs text-muted-foreground font-mono">@{selectedProfile.acct}</p>

                {/* Bio / Note */}
                {selectedProfile.note && (
                  <div
                    className="text-xs text-foreground/90 my-3 leading-relaxed break-words border-t border-b border-border/20 py-2"
                    dangerouslySetInnerHTML={{ __html: selectedProfile.note }}
                  />
                )}

                {/* Metrics */}
                <div className="flex gap-4 text-xs text-muted-foreground my-2 font-medium">
                  <div>
                    <strong className="text-foreground">{selectedProfile.statuses_count}</strong> Posts
                  </div>
                  <div>
                    <strong className="text-foreground">{selectedProfile.following_count}</strong> Siguiendo
                  </div>
                  <div>
                    <strong className="text-foreground">{selectedProfile.followers_count}</strong> Seguidores
                  </div>
                </div>
              </div>

              {/* User Toots */}
              <div className="border-t border-border/20 p-4 bg-background/30 space-y-3">
                <h4 className="text-xs font-bold text-foreground uppercase tracking-wider">Publicaciones recientes</h4>
                {profileToots.length > 0 ? (
                  profileToots.map(t => (
                    <div key={t.id} className="bg-card/40 border border-border/30 rounded-xl p-3 text-xs space-y-2">
                      <div dangerouslySetInnerHTML={{ __html: t.content }} />
                      <span className="text-[10px] text-muted-foreground block">
                        {new Date(t.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted-foreground italic">No hay publicaciones disponibles.</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    )}
    </>
  );
}

