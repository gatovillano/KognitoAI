"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import apiClient from "@/lib/api";
import { Trash2, Loader2 } from "lucide-react";

interface Permission {
  account_id: string;
  email: string;
  role: "owner" | "editor" | "viewer";
}

interface ShareWorkspaceDialogProps {
  workspaceId: string;
  workspaceName: string;
  isOpen: boolean;
  onClose: () => void;
  onPermissionsUpdated: () => void;
}

export function ShareWorkspaceDialog({
  workspaceId,
  workspaceName,
  isOpen,
  onClose,
  onPermissionsUpdated,
}: ShareWorkspaceDialogProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"editor" | "viewer">("editor");
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const { toast } = useToast();

  const fetchPermissions = useCallback(async () => {
    if (!workspaceId) return;
    setIsLoading(true);
    try {
      const response = await apiClient.get(`/api/workspaces/${workspaceId}/permissions`);
      setPermissions(response.data);
    } catch (error) {
      console.error("Error fetching permissions:", error);
      toast({
        title: "Error",
        description: "No se pudieron cargar los permisos del workspace.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  }, [workspaceId, toast]);

  useEffect(() => {
    if (isOpen) {
      fetchPermissions();
    }
  }, [isOpen, fetchPermissions]);

  const handleInvite = async () => {
    if (!email) {
      toast({ title: "Error", description: "Por favor, introduce un email.", variant: "destructive" });
      return;
    }
    setIsInviting(true);
    try {
      // Asumimos que la API puede encontrar el account_id por el email.
      // En un caso real, podríamos necesitar un endpoint /api/users/find-by-email
      await apiClient.post(`/api/workspaces/${workspaceId}/share`, { email, role });
      toast({
        title: "¡Éxito!",
        description: `Se ha invitado a ${email} como ${role}.`,
      });
      setEmail("");
      fetchPermissions(); // Recargar la lista de miembros
      onPermissionsUpdated(); // Notificar a la página principal para que se actualice si es necesario
    } catch (error: any) {
      console.error("Error inviting user:", error);
      toast({
        title: "Error al invitar",
        description: error.response?.data?.detail || "No se pudo invitar al usuario.",
        variant: "destructive",
      });
    } finally {
      setIsInviting(false);
    }
  };

  const handleRoleChange = async (accountId: string, newRole: "editor" | "viewer") => {
    try {
      await apiClient.put(`/api/workspaces/${workspaceId}/permissions/${accountId}`, { role: newRole });
      toast({
        title: "Rol actualizado",
        description: "El rol del usuario ha sido actualizado.",
      });
      fetchPermissions();
      onPermissionsUpdated();
    } catch (error: any) {
      console.error("Error updating role:", error);
      toast({
        title: "Error al actualizar",
        description: error.response?.data?.detail || "No se pudo cambiar el rol.",
        variant: "destructive",
      });
    }
  };

  const handleRevokeAccess = async (accountId: string) => {
    try {
      await apiClient.delete(`/api/workspaces/${workspaceId}/permissions/${accountId}`);
      toast({
        title: "Acceso revocado",
        description: "Se ha eliminado al usuario del workspace.",
      });
      fetchPermissions();
      onPermissionsUpdated();
    } catch (error: any) {
      console.error("Error revoking access:", error);
      toast({
        title: "Error al revocar",
        description: error.response?.data?.detail || "No se pudo revocar el acceso.",
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Compartir: {workspaceName}</DialogTitle>
          <DialogDescription>
            Invita a otros usuarios y gestiona los permisos de acceso.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-6 py-4">
          <div className="flex items-center space-x-2">
            <Input
              id="email"
              placeholder="Email del usuario a invitar"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="flex-1"
              disabled={isInviting}
            />
            <Select value={role} onValueChange={(value) => setRole(value as "editor" | "viewer")} disabled={isInviting}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Rol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="editor">Editor</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleInvite} disabled={isInviting}>
              {isInviting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Invitar
            </Button>
          </div>
          <div className="space-y-2">
            <h4 className="font-medium">Miembros Actuales</h4>
            <div className="rounded-md border max-h-60 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Usuario</TableHead>
                    <TableHead className="w-[150px]">Rol</TableHead>
                    <TableHead className="text-right w-[50px]">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {isLoading ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center">
                        <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  ) : permissions.length > 0 ? (
                    permissions.map((p) => (
                      <TableRow key={p.account_id}>
                        <TableCell className="font-medium">{p.email}</TableCell>
                        <TableCell>
                          {p.role === 'owner' ? (
                            <span className="font-semibold">Propietario</span>
                          ) : (
                            <Select
                              value={p.role}
                              onValueChange={(newRole) => handleRoleChange(p.account_id, newRole as "editor" | "viewer")}
                            >
                              <SelectTrigger className="w-full">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="editor">Editor</SelectItem>
                                <SelectItem value="viewer">Viewer</SelectItem>
                              </SelectContent>
                            </Select>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {p.role !== 'owner' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-destructive"
                              onClick={() => handleRevokeAccess(p.account_id)}
                              title="Revocar acceso"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell colSpan={3} className="text-center text-muted-foreground">
                        Solo tú tienes acceso a este workspace.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}