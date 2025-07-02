"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/lib/api";

interface Collection {
  topic: string;
  document_count: number;
}

interface Workspace {
  id: string;
  name: string;
}

interface GitHubRepoDialogProps {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  onSuccess: () => void;
}

export function GitHubRepoDialog({ isOpen, onOpenChange, onSuccess }: GitHubRepoDialogProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedCollection, setSelectedCollection] = useState<string | null>(null);
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null);
  const [collectionTopic, setCollectionTopic] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    if (isOpen) {
      const fetchData = async () => {
        try {
          const [collectionsResponse, workspacesResponse] = await Promise.all([
            apiClient.post("/api/list-collections"),
            apiClient.get("/api/workspaces")
          ]);
          setCollections(collectionsResponse.data);
          setWorkspaces(workspacesResponse.data);
        } catch (error) {
          toast({
            title: "Error",
            description: "No se pudieron cargar los datos.",
            variant: "destructive",
          });
        }
      };
      fetchData();
    }
  }, [isOpen, toast]);

  const handleManageCollection = async (action: "add_as_knowledge_collection" | "update_knowledge_collection") => {
    if (!repoUrl) {
      toast({
        title: "Error",
        description: "Por favor, introduce la URL del repositorio.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiClient.post("/api/github/collections", {
        repo_url: repoUrl,
        action,
        github_token: githubToken,
        collection_topic: collectionTopic || "repositorio",
        workspace_id: selectedWorkspace,
      });
      toast({
        title: "Éxito",
        description: response.data.message,
      });
      onSuccess();
      onOpenChange(false);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Ocurrió un error al gestionar la colección.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Gestionar Repositorio de GitHub</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div>
            <Label htmlFor="repo-url">URL del Repositorio</Label>
            <Input
              id="repo-url"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/usuario/repositorio"
            />
          </div>
          <div>
            <Label htmlFor="github-token">Token de GitHub (opcional)</Label>
            <Input
              id="github-token"
              type="password"
              value={githubToken}
              onChange={(e) => setGithubToken(e.target.value)}
              placeholder="Para repositorios privados"
            />
          </div>
          <div>
            <Label htmlFor="collection-topic">Tema de la Colección</Label>
            <Input
              id="collection-topic"
              value={collectionTopic}
              onChange={(e) => setCollectionTopic(e.target.value)}
              placeholder="repositorio (por defecto)"
            />
            <p className="text-sm text-muted-foreground mt-1">
              Tema bajo el cual se organizará este repositorio.
            </p>
          </div>
          <div>
            <Label htmlFor="workspace-select">Workspace (opcional)</Label>
            <Select value={selectedWorkspace || ""} onValueChange={setSelectedWorkspace}>
              <SelectTrigger id="workspace-select">
                <SelectValue placeholder="Seleccionar workspace o dejar en blanco para uso personal" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Personal (sin workspace)</SelectItem>
                {workspaces.map((workspace) => (
                  <SelectItem key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-sm text-muted-foreground mt-1">
              Si seleccionas un workspace, el repositorio estará disponible solo en ese workspace.
            </p>
          </div>
        </div>
        <DialogFooter>
          <Button
            onClick={() => handleManageCollection("add_as_knowledge_collection")}
            disabled={isLoading}
          >
            {isLoading ? "Añadiendo..." : "Añadir"}
          </Button>
          <Button
            onClick={() => handleManageCollection("update_knowledge_collection")}
            disabled={isLoading}
            variant="outline"
          >
            {isLoading ? "Actualizando..." : "Actualizar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
