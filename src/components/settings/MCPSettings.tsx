"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';
import apiClient from '@/lib/api';
import { Plus, Trash2, Plug, Unplug, Server, AlertCircle } from 'lucide-react';

interface MCPServer {
  id: string;
  name: string;
  transport_type: string;
  command?: string;
  args?: string[];
  url?: string;
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

  const handleAddServer = async () => {
    if (!name) {
      toast.error('El nombre es obligatorio');
      return;
    }
    if (transportType === 'stdio' && !command) {
      toast.error('El comando es obligatorio para stdio');
      return;
    }
    if (transportType === 'sse' && !url) {
      toast.error('La URL es obligatoria para sse');
      return;
    }

    try {
      const args = argsStr ? argsStr.split(' ').filter(a => a.trim() !== '') : [];
      await apiClient.post('/api/mcp-servers', {
        name,
        transport_type: transportType,
        command: transportType === 'stdio' ? command : undefined,
        args: transportType === 'stdio' ? args : undefined,
        url: transportType === 'sse' ? url : undefined,
      });
      toast.success('Servidor MCP añadido con éxito');
      setIsAdding(false);
      setName('');
      setCommand('');
      setArgsStr('');
      setUrl('');
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
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {transportType === 'stdio' ? (
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
              ) : (
                <div className="space-y-2">
                  <Label>URL del servidor SSE</Label>
                  <Input value={url} onChange={e => setUrl(e.target.value)} placeholder="Ej: http://localhost:8080/sse" />
                </div>
              )}
              
              <Button onClick={handleAddServer}>Guardar Servidor</Button>
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
                <Card key={server.id} className="border shadow-sm flex flex-col">
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
                  <CardFooter className="pt-2 mt-auto flex justify-between bg-muted/50 border-t">
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
    </div>
  );
};
