"use client";

import React, { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { User, Mail, KeyRound, Edit, Trash2 } from "lucide-react";
import apiClient from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

interface ShareWorkspaceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: string;
  workspaceName: string;
  onPermissionsUpdated: () => void; // Callback para notificar a page.tsx
}

type Role = "owner" | "editor" | "viewer";

interface PermissionResponse {
  account_id: string;
  email: string;
  role: Role;
}

interface ShareWorkspaceRequest {
  email: string;
  role: Role;
}

const ShareWorkspaceDialog: React.FC<ShareWorkspaceDialogProps> = ({
  isOpen,
  onClose,
  workspaceId,
  workspaceName,
  onPermissionsUpdated,
}) => {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [permissions, setPermissions] = useState<PermissionResponse[]>([]);
  const [loadingPermissions, setLoadingPermissions] = useState(true);
  const { toast } = useToast();

  const fetchPermissions = async () => {
    if (!workspaceId) return;
    setLoadingPermissions(true);
    try {
      const response = await apiClient.get<PermissionResponse[]>(
        `/api/workspaces/${workspaceId}/permissions`
      );
      setPermissions(response.data);
    } catch (error) {
      console.error("Error fetching permissions:", error);
      toast({
        title: "Error",
        description: "No se pudieron cargar los permisos del workspace.",
        variant: "destructive",
      });
    } finally {
      setLoadingPermissions(false);
    }
  };

  useEffect(() => {
    if (isOpen && workspaceId) {
      fetchPermissions();
    }
  }, [isOpen, workspaceId]);

  const handleInvite = async () => {
    setIsSubmitting(true);
    try {
      // Asumimos que el backend resuelve account_id a partir del email
      await apiClient.post(`/api/workspaces/${workspaceId}/share`, {
        email,
        role,
      } as ShareWorkspaceRequest);
      toast({
        title: "Éxito",
        description: `Usuario ${email} invitado como ${role}.`,
      });
      setEmail("");
      setRole("viewer");
      fetchPermissions(); // Recargar permisos
      onPermissionsUpdated();
    } catch (error: any) {
      console.error("Error inviting user:", error);
      toast({
        title: "Error",
        description:
          error.response?.data?.detail || "No se pudo invitar al usuario.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEditPermission = async (
    accountId: string,
    newRole: Role
  ) => {
    setIsSubmitting(true);
    try {
      await apiClient.put(
        `/api/workspaces/${workspaceId}/permissions/${accountId}`,
        { role: newRole }
      );
      toast({
        title: "Éxito",
        description: `Permiso de usuario actualizado a ${newRole}.`,
      });
      fetchPermissions(); // Recargar permisos
      onPermissionsUpdated();
    } catch (error: any) {
      console.error("Error updating permission:", error);
      toast({
        title: "Error",
        description:
          error.response?.data?.detail ||
          "No se pudo actualizar el permiso del usuario.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRevokePermission = async (accountId: string) => {
    setIsSubmitting(true);
    try {
      await apiClient.delete(
        `/api/workspaces/${workspaceId}/permissions/${accountId}`
      );
      toast({
        title: "Éxito",
        description: "Acceso de usuario revocado.",
      });
      fetchPermissions(); // Recargar permisos
      onPermissionsUpdated();
    } catch (error: any) {
      console.error("Error revoking permission:", error);
      toast({
        title: "Error",
        description:
          error.response?.data?.detail ||
          "No se pudo revocar el acceso del usuario.",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Compartir Workspace: {workspaceName}</DialogTitle>
          <DialogDescription>
            Gestiona el acceso y los permisos para este workspace.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4">
          <h3 className="text-lg font-medium">Invitar usuario</h3>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="email" className="text-right">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="col-span-3"
              placeholder="email@example.com"
            />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="role" className="text-right">
              Rol
            </Label>
            <Select
              value={role}
              onValueChange={(value: Role) =>
                setRole(value)
              }
            >
              <SelectTrigger className="col-span-3">
                <SelectValue placeholder="Selecciona un rol" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="owner">Owner</SelectItem>
                <SelectItem value="editor">Editor</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button onClick={handleInvite} disabled={isSubmitting || !email}>
            {isSubmitting ? "Invitando..." : "Invitar"}
          </Button>
        </div>

        <Separator className="my-4" />

        <div className="grid gap-4 py-4">
          <h3 className="text-lg font-medium">Permisos existentes</h3>
          {loadingPermissions ? (
            <p className="text-center text-gray-500">Cargando permisos...</p>
          ) : permissions.length === 0 ? (
            <p className="text-center text-gray-500">
              No hay usuarios con acceso a este workspace.
            </p>
          ) : (
            <div className="space-y-2">
              {permissions.map((permission) => (
                <div
                  key={permission.account_id}
                  className="flex items-center justify-between rounded-md border p-3"
                >
                  <div className="flex items-center space-x-2">
                    <Mail className="h-4 w-4 text-gray-500" />
                    <span className="font-medium">{permission.email}</span>
                    <KeyRound className="h-4 w-4 text-gray-500" />
                    <Select
                      value={permission.role}
                      onValueChange={(newRole: Role) =>
                        handleEditPermission(permission.account_id, newRole)
                      }
                      disabled={isSubmitting}
                    >
                      <SelectTrigger className="w-[120px] h-8 text-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="owner">Owner</SelectItem>
                        <SelectItem value="editor">Editor</SelectItem>
                        <SelectItem value="viewer">Viewer</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() =>
                        handleRevokePermission(permission.account_id)
                      }
                      disabled={isSubmitting}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default ShareWorkspaceDialog;