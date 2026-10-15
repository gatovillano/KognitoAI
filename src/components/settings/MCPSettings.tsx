"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Plus, Trash2, Plug, Unplug, Server, AlertCircle, Puzzle, RefreshCw } from 'lucide-react';

interface MCPServer {
  id: string;
  name: string;
  transport_type: string;
  command?: string;
  args?: string[];
  url?: string;
  env?: Record<string, string>;
  headers?: Record<string, string>;
  status: string;
}

export const MCPSettings = () => {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Form state
  const [isAdding, setIsAdding] = useState(false);
  const [name, setName] = useState('');
  const [transportType, setTransportType] = useState('stdio');
  const [command, setCommand] = useState('');
  const [argsStr, setArgsStr] = useState('');
  const [url, setUrl] = useState('');
  const [envStr, setEnvStr] = useState('');
  const [headersStr, setHeadersStr] = useState('');
  // JSON import state
  const [importJson, setImportJson] = useState('');
  const [importing, setImporting] = useState(false);
  // JSON paste-to-form state
  const [pasteJson, setPasteJson] = useState('');

  const fetchServers = async () => {
    try {
      const response = await apiClient.get<MCPServer[]>('/api/mcp-servers');
      setServers(response.data);
    } catch (error) {
      console.error('Error fetching MCP servers:', error);
      toast.error('Error al cargar servidores MCP');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServers();
  }, []);

  const parseEnv = (raw: any): Record<string, string> | undefined => {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return undefined;
    const clean: Record<string, string> = {};
    for (const [k, v] of Object.entries(raw)) {
      if (v === null || v === undefined) continue;
      clean[String(k)] = String(v);
    }
    return Object.keys(clean).length > 0 ? clean : undefined;
  };

  const parseJsonConfig = (jsonText: string): MCPServer[] => {
    const parsed = JSON.parse(jsonText);
    // Acepta { mcpServers: { name: { command, args, url, env, headers, type } } }
    const serversObj = parsed?.mcpServers || parsed;
    if (!serversObj || typeof serversObj !== 'object') return [];
    const result: MCPServer[] = [];
    for (const [name, cfg] of Object.entries(serversObj)) {
      const c = cfg as any;
      const rawType = String(c?.type || c?.transport_type || '').toLowerCase();
      const t = rawType === 'http' || rawType.includes('streamable') ? 'http'
        : c?.url ? (rawType || 'http')
        : (c?.transport_type || (c?.args?.some((a: string) => a.includes('sse')) ? 'sse' : 'stdio'));
      result.push({
        id: '',
        name,
        transport_type: t,
        command: c?.command,
        args: c?.args,
        url: c?.url,
        env: parseEnv(c?.env),
        headers: parseEnv(c?.headers),
        status: 'disconnected',
      });
    }
    return result;
  };

  const handleImportJson = async () => {
    if (!importJson.trim()) {
      toast.error('Pega primero un JSON válido');
      return;
    }
    setImporting(true);
    try {
      const imported = parseJsonConfig(importJson);
      if (imported.length === 0) {
        toast.error('No se encontraron servidores en el JSON');
        return;
      }
      // Importar cada servidor vía API
      for (const s of imported) {
        const args = s.args || [];
        await apiClient.post('/api/mcp-servers', {
          name: s.name,
          transport_type: s.transport_type,
          command: s.command,
          args,
          url: s.url,
          env: s.env,
          headers: s.headers,
        });
      }
      toast.success(`${imported.length} servidor(es) importado(s) correctamente`);
      setImportJson('');
      fetchServers();
    } catch (e: any) {
      console.error('Error importing JSON:', e);
      toast.error('Error al importar JSON: ' + (e?.response?.data?.detail || e.message));
    } finally {
      setImporting(false);
    }
  };

  /**
   * Parse un JSON de servidor MCP y rellena el formulario de "Añadir Servidor"
   * para que el usuario pueda revisar y guardar manualmente.
   * Acepta: { "mcpServers": { "name": { command, args, url, env, headers, type } } }
   */
  const loadFromJson = () => {
    if (!pasteJson.trim()) {
      toast.error('Pega primero un JSON válido');
      return;
    }
    try {
      const parsed = JSON.parse(pasteJson);
      const serversObj = parsed?.mcpServers || parsed;
      if (!serversObj || typeof serversObj !== 'object') {
        toast.error('JSON inválido: se esperaba un objeto con mcpServers');
        return;
      }
      // Tomar el primer servidor encontrado
      const [[name, cfg]] = Object.entries(serversObj);
      const c = cfg as any;
      const rawType = String(c?.type || c?.transport_type || '').toLowerCase();
      const tType = rawType === 'http' || rawType.includes('streamable') ? 'http' : (c?.url ? (rawType || 'http') : 'stdio');
      setName(name);
      setTransportType(tType);
      setCommand(c?.command || '');
      setArgsStr(Array.isArray(c?.args) ? c.args.join(' ') : '');
      setUrl(c?.url || '');
      setEnvStr(c?.env && typeof c.env === 'object' ? JSON.stringify(c.env, null, 2) : '');
      setHeadersStr(c?.headers && typeof c.headers === 'object' ? JSON.stringify(c.headers, null, 2) : '');
      toast.success(`Servidor "${name}" cargado en el formulario`);
      setPasteJson('');
    } catch (e: any) {
      toast.error('Error al parsear JSON: ' + (e?.message || 'JSON inválido'));
    }
  };

  const handleAddServer = async () => {
    if (!name) {
      toast.error('El nombre es obligatorio');
      return;
    }
    if (transportType === 'stdio' && !command) {
      toast.error('El comando es obligatorio para stdio');
      return;
    }
    if ((transportType === 'sse' || transportType === 'http') && !url) {
      toast.error('La URL es obligatoria para sse/http');
      return;
    }

    try {
      const args = argsStr ? argsStr.split(' ').filter(a => a.trim() !== '') : [];
      let env: Record<string, string> | undefined = undefined;
      if (envStr.trim()) {
        try {
          const parsedEnv = JSON.parse(envStr);
          env = parseEnv(parsedEnv);
          if (!env) throw new Error('env vacío');
        } catch {
          toast.error('Env JSON inválido. Debe ser objeto {"KEY":"value"}');
          return;
        }
      }
      let headers: Record<string, string> | undefined = undefined;
      if (headersStr.trim()) {
        try {
          const parsedH = JSON.parse(headersStr);
          headers = parseEnv(parsedH);
          if (!headers) throw new Error('headers vacío');
        } catch {
          toast.error('Headers JSON inválido. Debe ser objeto {"Authorization":"Basic ..."}');
          return;
        }
      }
      await apiClient.post('/api/mcp-servers', {
        name,
        transport_type: transportType,
        command: transportType === 'stdio' ? command : undefined,
        args: transportType === 'stdio' ? args : undefined,
        url: transportType !== 'stdio' ? url : undefined,
        env,
        headers,
      });
      toast.success('Servidor MCP añadido con éxito');
      setIsAdding(false);
      setName('');
      setCommand('');
      setArgsStr('');
      setUrl('');
      setEnvStr('');
      setHeadersStr('');
      fetchServers();
    } catch (error) {
      console.error('Error adding MCP server:', error);
      toast.error('Error al añadir el servidor MCP');
    }
  };

  const handleDeleteServer = async (id: string) => {
    try {
      await apiClient.delete(`/api/mcp-servers/${id}`);
      toast.success('Servidor eliminado');
      fetchServers();
    } catch (error) {
      toast.error('Error al eliminar servidor');
    }
  };

  const handleConnect = async (id: string) => {
    try {
      await apiClient.post(`/api/mcp-servers/${id}/connect`);
      toast.success('Comando de conexión enviado');
      fetchServers();
    } catch (error) {
      toast.error('Error al conectar servidor');
    }
  };

  const handleDisconnect = async (id: string) => {
    try {
      await apiClient.post(`/api/mcp-servers/${id}/disconnect`);
      toast.success('Servidor desconectado');
      fetchServers();
    } catch (error) {
      toast.error('Error al desconectar servidor');
    }
  };

  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [tools, setTools] = useState<Array<{ name: string; description: string; server: string | null }>>([]);
  const [toolsLoading, setToolsLoading] = useState(false);
  const [toolsError, setToolsError] = useState<string | null>(null);

  const extractTools = (data: any): Array<{ name: string; description: string; server: string | null }> => {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.tools)) return data.tools;
    return [];
  };

  const fetchTools = async (serverId: string, serverName?: string) => {
    setToolsLoading(true);
    setToolsError(null);
    try {
      // 1) Endpoint por servidor: funciona aunque el servidor esté desconectado
      //    (el backend intenta conectar y devuelve error explicativo si falla).
      try {
        const response = await apiClient.get(`/api/mcp-servers/${serverId}/tools`);
        console.log("MCP /{id}/tools response:", response.data);
        if (response.data?.error) {
          setToolsError(response.data.error);
        }
        const serverTools = extractTools(response.data);
        setTools(serverTools);
        // Refrescar estado del servidor en la lista (puede haber cambiado a connected/error)
        if (response.data?.status) {
          setServers((prev) => prev.map((s) => s.id === serverId ? { ...s, status: response.data.status } : s));
          setSelectedServer((prev) => prev && prev.id === serverId ? { ...prev, status: response.data.status } : prev);
        }
        return;
      } catch (perServerError: any) {
        // Si el endpoint por servidor no existe (backend antiguo) o falla con 404/405,
        // caer al endpoint global como fallback.
        const status = perServerError?.response?.status;
        console.warn(`Per-server tools endpoint failed (${status}), fallback a /tools global`, perServerError?.response?.data);
        if (status && status !== 404 && status !== 405 && status !== 422) {
          // Error real del servidor concreto (p.ej. 500): mostrarlo sin fallback confuso.
          throw perServerError;
        }
      }

      // 2) Fallback: endpoint global + filtrado en cliente.
      const response = await apiClient.get(`/api/mcp-servers/tools`);
      console.log("MCP /tools response:", response.data);
      const allTools = extractTools(response.data);
      
      const targetId = String(serverId || '').toLowerCase().trim();
      const targetName = String(serverName || '').toLowerCase().trim();

      const hasServerInfo = allTools.some((t: any) => t.server_id || t.serverId || t.server || t.serverName);
      if (!hasServerInfo) {
        // Backend antiguo sin server_id: no se puede filtrar, mostrar todas.
        setTools(allTools);
      } else {
        const matching = allTools.filter((t: any) => {
          const toolServerId = String(t.server_id || t.serverId || '').toLowerCase().trim();
          const toolServerName = String(t.server || t.serverName || '').toLowerCase().trim();
          return (
            (toolServerId && toolServerId === targetId) ||
            (toolServerName && targetName && toolServerName === targetName) ||
            (toolServerName && toolServerName === targetId)
          );
        });

        console.log(`Matching tools for server ${serverName} (${serverId}):`, matching);
        setTools(matching);
      }
    } catch (error) {
      console.error('Error fetching tools:', error);
      toast.error('Error al cargar las herramientas del servidor');
      setTools([]);
    } finally {
      setToolsLoading(false);
    }
  };

  const openToolsDialog = async (server: MCPServer) => {
    setSelectedServer(server);
    setTools([]);
    setToolsError(null);
    await fetchTools(server.id, server.name);
  };

  if (loading) {
    return <div>Cargando servidores MCP...</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <div>
              <CardTitle>Servidores MCP (Model Context Protocol)</CardTitle>
              <CardDescription>
                Conecta herramientas externas a Kognito AI utilizando el estándar MCP.
              </CardDescription>
            </div>
            <Button onClick={() => setIsAdding(!isAdding)} variant={isAdding ? "outline" : "default"}>
              {isAdding ? "Cancelar" : <><Plus className="h-4 w-4 mr-2" /> Añadir Servidor</>}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isAdding && (
            <div className="bg-muted p-4 rounded-lg space-y-4 mb-6 border">
              <h3 className="font-medium">Nuevo Servidor MCP</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Nombre</Label>
                  <Input value={name} onChange={e => setName(e.target.value)} placeholder="Ej: SQLite Local" />
                </div>
                <div className="space-y-2">
                  <Label>Tipo de Transporte</Label>
                  <Select value={transportType} onValueChange={setTransportType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="stdio">Stdio (Local command)</SelectItem>
                      <SelectItem value="sse">SSE (HTTP URL)</SelectItem>
                      <SelectItem value="http">Streamable HTTP (POST)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {transportType === 'stdio' ? (
                <>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Comando</Label>
                    <Input value={command} onChange={e => setCommand(e.target.value)} placeholder="Ej: npx" />
                  </div>
                  <div className="space-y-2">
                    <Label>Argumentos (separados por espacio)</Label>
                    <Input value={argsStr} onChange={e => setArgsStr(e.target.value)} placeholder="Ej: -y @modelcontextprotocol/server-sqlite /path/to/db.sqlite" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Variables de entorno (JSON)</Label>
                  <textarea
                    className="w-full rounded-md border bg-background p-2 text-xs font-mono"
                    rows={3}
                    value={envStr}
                    onChange={(e) => setEnvStr(e.target.value)}
                    placeholder='{"WP_URL":"https://tusitio.com","WP_USERNAME":"user","WP_APP_PASSWORD":"xxxx xxxx"}'
                  />
                  <p className="text-xs text-muted-foreground">Se guarda en backend y se inyecta al proceso MCP. No se muestra en la lista.</p>
                </div>
                </>
              ) : (
                <>
                <div className="space-y-2">
                  <Label>{transportType === 'http' ? 'URL del servidor Streamable HTTP' : 'URL del servidor SSE'}</Label>
                  <Input value={url} onChange={e => setUrl(e.target.value)} placeholder="Ej: https://tusitio.com/wp-json/elementor/mcp/" />
                </div>
                <div className="space-y-2">
                  <Label>Headers HTTP (JSON)</Label>
                  <textarea
                    className="w-full rounded-md border bg-background p-2 text-xs font-mono"
                    rows={3}
                    value={headersStr}
                    onChange={(e) => setHeadersStr(e.target.value)}
                    placeholder='{"Authorization":"Basic dXNlcjpwYXNz"}'
                  />
                  <p className="text-xs text-muted-foreground">Se envían en cada request HTTP (SSE o Streamable). Útil para Basic Auth de WordPress/Elementor.</p>
                </div>
                </>
              )}
              
              <Button onClick={handleAddServer}>Guardar Servidor</Button>

              {/* Importación por JSON (importa directo a la API) */}
              <div className="border-t pt-4 mt-4">
                <Label className="text-sm font-medium">Importar desde JSON (envía directo a la API)</Label>
                <textarea
                  className="w-full mt-1 rounded-md border bg-background p-2 text-xs font-mono"
                  rows={4}
                  value={importJson}
                  onChange={(e) => setImportJson(e.target.value)}
                  placeholder='{"mcpServers": {"map": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-map"]}}}'
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={handleImportJson}
                  disabled={importing || !importJson.trim()}
                >
                  {importing ? 'Importando...' : 'Importar JSON'}
                </Button>
              </div>

              {/* Carga rápida desde JSON: rellena el formulario */}
              <div className="border-t pt-4 mt-2">
                <Label className="text-sm font-medium">Cargar JSON en formulario</Label>
                <textarea
                  className="w-full mt-1 rounded-md border bg-background p-2 text-xs font-mono"
                  rows={4}
                  value={pasteJson}
                  onChange={(e) => setPasteJson(e.target.value)}
                  placeholder='{"mcpServers": {"map": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-map"]}}}'
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="mt-2"
                  onClick={loadFromJson}
                  disabled={!pasteJson.trim()}
                >
                  Cargar en formulario
                </Button>
              </div>
            </div>
          )}

          {servers.length === 0 && !isAdding ? (
            <div className="text-center py-8 text-muted-foreground">
              <Server className="h-12 w-12 mx-auto mb-3 opacity-20" />
              <p>No tienes ningún servidor MCP configurado.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {servers.map((server) => (
                <Card key={server.id} className="border shadow-sm flex flex-col cursor-pointer hover:border-primary/40 hover:shadow-md transition-all duration-200" onClick={() => openToolsDialog(server)}>
                  <CardHeader className="pb-2">
                    <div className="flex justify-between items-start">
                      <CardTitle className="text-lg flex items-center gap-2">
                        {server.name}
                      </CardTitle>
                      <div className="flex items-center">
                        {server.status === 'connected' ? (
                          <span className="flex h-2 w-2 rounded-full bg-green-500 mr-2"></span>
                        ) : server.status === 'error' ? (
                          <span className="flex h-2 w-2 rounded-full bg-red-500 mr-2"></span>
                        ) : (
                          <span className="flex h-2 w-2 rounded-full bg-slate-400 mr-2"></span>
                        )}
                        <span className="text-xs text-muted-foreground capitalize">{server.status}</span>
                      </div>
                    </div>
                    <CardDescription className="text-xs mt-1">
                      {server.transport_type === 'stdio' ? (
                        <>Command: <code className="bg-muted px-1 py-0.5 rounded">{server.command} {server.args?.join(' ')}</code></>
                      ) : (
                        <>URL: {server.url}</>
                      )}
                    </CardDescription>
                  </CardHeader>
                  <CardFooter className="pt-2 mt-auto flex justify-between bg-muted/50 border-t" onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-2">
                      {server.status === 'connected' ? (
                        <Button size="sm" variant="outline" onClick={() => handleDisconnect(server.id)} className="h-8">
                          <Unplug className="h-3.5 w-3.5 mr-1" /> Desconectar
                        </Button>
                      ) : (
                        <Button size="sm" variant="outline" onClick={() => handleConnect(server.id)} className="h-8">
                          <Plug className="h-3.5 w-3.5 mr-1" /> Conectar
                        </Button>
                      )}
                    </div>
                    <Button size="sm" variant="ghost" className="text-red-500 hover:text-red-700 h-8 px-2" onClick={() => handleDeleteServer(server.id)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {selectedServer && (
        <Dialog open={!!selectedServer} onOpenChange={(open) => !open && setSelectedServer(null)}>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-3">
                <Server className="h-5 w-5 text-primary" />
                {selectedServer.name}
              </DialogTitle>
              <DialogDescription>
                {selectedServer.status === 'connected' ? (
                  <span className="flex items-center gap-2">
                    <span className="flex h-2 w-2 rounded-full bg-green-500"></span>
                    Conectado
                  </span>
                ) : selectedServer.status === 'error' ? (
                  <span className="flex items-center gap-2 text-red-500">
                    <span className="flex h-2 w-2 rounded-full bg-red-500"></span>
                    Error de conexión
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-slate-400">
                    <span className="flex h-2 w-2 rounded-full bg-slate-400"></span>
                    Desconectado
                  </span>
                )}
                {" — "}{selectedServer.transport_type === 'stdio' ? 'Stdio' : 'SSE'}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="bg-muted/50 rounded-lg p-4">
                <h4 className="text-sm font-medium mb-2">Configuración</h4>
                {selectedServer.status === 'error' && (
                  <div className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2 rounded">
                    <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                    <span>Este servidor muestra errores. Verifica la configuración del comando o la URL y reconecta.</span>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Tipo:</span> <code className="bg-muted px-1.5 py-0.5 rounded text-xs">{selectedServer.transport_type}</code>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Estado:</span> <span className="capitalize">{selectedServer.status}</span>
                  </div>
                  {selectedServer.status === 'connected' && (
                    <div className="col-span-2">
                      <span className="text-muted-foreground">Comando / URL:</span>
                      {selectedServer.transport_type === 'stdio' ? (
                        <code className="block bg-muted/70 px-2 py-1.5 rounded mt-1 text-xs font-mono break-all">
                          {selectedServer.command} {selectedServer.args?.join(' ')}
                        </code>
                      ) : (
                        <code className="block bg-muted/70 px-2 py-1.5 rounded mt-1 text-xs font-mono break-all">{selectedServer.url}</code>
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                  <Puzzle className="h-4 w-4" />
                  Herramientas disponibles ({tools.length})
                </h4>
                {toolsLoading ? (
                  <div className="text-center py-6 text-muted-foreground">
                    <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2" />
                    <p>Cargando herramientas...</p>
                  </div>
                ) : tools.length === 0 ? (
                  <div className="text-center py-6 text-muted-foreground border border-dashed rounded-lg">
                    <Server className="h-10 w-10 mx-auto mb-2 opacity-30" />
                    <p>No se encontraron herramientas para este servidor.</p>
                    {toolsError ? (
                      <p className="text-xs mt-1 text-amber-600 dark:text-amber-400">{toolsError}</p>
                    ) : (
                      <p className="text-xs mt-1">Conecta el servidor para que el agente pueda usar sus herramientas.</p>
                    )}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 gap-3 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
                    {tools.map((tool, idx) => (
                      <div key={idx} className="border rounded-lg p-3 hover:bg-accent/50 transition-colors">
                        <div className="flex flex-col gap-1">
                          <code className="bg-muted px-1.5 py-0.5 rounded text-xs font-semibold text-primary w-fit font-mono">
                            {tool.name}
                          </code>
                          {tool.description ? (
                            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{tool.description}</p>
                          ) : (
                            <p className="text-xs text-muted-foreground italic">Sin descripción</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSelectedServer(null)}>Cerrar</Button>
              {selectedServer.status === 'connected' ? (
                <Button size="sm" variant="outline" onClick={() => handleDisconnect(selectedServer.id)} className="h-9">
                  <Unplug className="h-3.5 w-3.5 mr-1" /> Desconectar
                </Button>
              ) : (
                <Button size="sm" onClick={() => handleConnect(selectedServer.id)} className="h-9">
                  <Plug className="h-3.5 w-3.5 mr-1" /> Conectar
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
