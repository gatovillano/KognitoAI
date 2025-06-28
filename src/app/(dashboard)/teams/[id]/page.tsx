"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Users, UserPlus, UserMinus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import apiClient from "@/lib/api";
import { useToast } from "@/hooks/use-toast";

export default function TeamDetailPage() {
  const router = useRouter();
  const params = useParams();
  const teamId = params.id as string;
  const [team, setTeam] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [documents, setDocuments] = useState<any[]>([]);
  const [notes, setNotes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [resourcesLoading, setResourcesLoading] = useState(true);
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [removeMemberOpen, setRemoveMemberOpen] = useState(false);
  const [memberIdentifier, setMemberIdentifier] = useState("");
  const [selectedMember, setSelectedMember] = useState<any>(null);
  const [searching, setSearching] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const fetchTeamDetails = async () => {
      try {
        const teamResponse = await apiClient.get(`/api/teams/${teamId}`);
        setTeam(teamResponse.data);
        const membersResponse = await apiClient.get(`/api/teams/${teamId}/members`);
        setMembers(membersResponse.data);
      } catch (error: any) {
        console.error("Error fetching team details:", error.response?.data || error.message || error);
        toast({
          title: "Error",
          description: "No se pudieron cargar los detalles del equipo. Revisa la consola para más detalles.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };
    fetchTeamDetails();
  }, [teamId, toast]);

  useEffect(() => {
    const fetchTeamResources = async () => {
      if (!team) return;
      setResourcesLoading(true);
      try {
        const documentsResponse = await apiClient.get(`/api/teams/${teamId}/documents`);
        setDocuments(documentsResponse.data);
        const notesResponse = await apiClient.get(`/api/teams/${teamId}/notes`);
        setNotes(notesResponse.data);
      } catch (error: any) {
        console.error("Error fetching team resources:", error.response?.data || error.message || error);
        toast({
          title: "Error",
          description: "No se pudieron cargar los recursos compartidos del equipo. Revisa la consola para más detalles.",
          variant: "destructive",
        });
      } finally {
        setResourcesLoading(false);
      }
    };
    fetchTeamResources();
  }, [team, teamId, toast]);

  const handleAddMember = async () => {
    try {
      setSearching(true);
      // Search for user by username or email to get account_id
      const searchResponse = await apiClient.get(`/api/users/search`, { params: { identifier: memberIdentifier } });
      if (searchResponse.data && searchResponse.data.account_id) {
        const accountId = searchResponse.data.account_id;
        await apiClient.post(`/api/teams/${teamId}/members`, { account_id: accountId });
        const membersResponse = await apiClient.get(`/api/teams/${teamId}/members`);
        setMembers(membersResponse.data);
        setMemberIdentifier("");
        setAddMemberOpen(false);
        toast({
          title: "Éxito",
          description: "Miembro añadido correctamente.",
        });
      } else {
        toast({
          title: "Error",
          description: "No se encontró un usuario con ese nombre o correo electrónico.",
          variant: "destructive",
        });
      }
    } catch (error: any) {
      console.error("Error adding member:", error.response?.data || error.message || error);
      if (error.response && error.response.status === 404) {
        toast({
          title: "Error",
          description: "La búsqueda de usuarios por nombre o correo no está disponible actualmente. Contacta al administrador.",
          variant: "destructive",
        });
      } else {
        toast({
          title: "Error",
          description: "No se pudo añadir el miembro. Revisa la consola para más detalles.",
          variant: "destructive",
        });
      }
    } finally {
      setSearching(false);
    }
  };

  const handleRemoveMember = async () => {
    if (!selectedMember) return;
    try {
      await apiClient.delete(`/api/teams/${teamId}/members`, { data: { account_id: selectedMember.account_id } });
      setMembers(members.filter(m => m.account_id !== selectedMember.account_id));
      setSelectedMember(null);
      setRemoveMemberOpen(false);
      toast({
        title: "Éxito",
        description: "Miembro eliminado correctamente.",
      });
    } catch (error: any) {
      console.error("Error removing member:", error.response?.data || error.message || error);
      toast({
        title: "Error",
        description: "No se pudo eliminar el miembro. Revisa la consola para más detalles.",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <p>Cargando detalles del equipo...</p>
      </div>
    );
  }

  if (!team) {
    return (
      <div className="p-6">
        <p>Equipo no encontrado o no tienes acceso a este equipo.</p>
        <Button onClick={() => router.push('/teams')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Equipos
        </Button>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center">
          <Users className="mr-2 h-6 w-6 text-blue-500" />
          <div>
            <h1 className="text-3xl font-bold mb-2">{team.name}</h1>
            <p className="text-muted-foreground">Gestiona los miembros y recursos de este equipo.</p>
          </div>
        </div>
        <Button onClick={() => router.push('/teams')} className="mt-4">
          <ArrowLeft className="mr-2 h-4 w-4" />
          Volver a Equipos
        </Button>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Miembros del Equipo</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex justify-between mb-4">
            <p className="text-muted-foreground">Lista de miembros actuales en el equipo.</p>
            <div className="space-x-2">
              <Button onClick={() => setAddMemberOpen(true)}>
                <UserPlus className="mr-2 h-4 w-4" />
                Añadir Miembro
              </Button>
              <Button variant="outline" onClick={() => setRemoveMemberOpen(true)} disabled={members.length === 0}>
                <UserMinus className="mr-2 h-4 w-4" />
                Eliminar Miembro
              </Button>
            </div>
          </div>
          {members.length === 0 ? (
            <p className="text-muted-foreground">No hay miembros en este equipo. Añade miembros para colaborar.</p>
          ) : (
            <div className="space-y-2">
              {members.map((member) => (
                <div key={member.account_id} className="flex items-center justify-between p-2 border rounded-md">
                  <p>ID de Cuenta: {member.account_id} {member.username ? `(${member.username})` : member.email ? `(${member.email})` : ''}</p>
                  <p className="text-muted-foreground">Unido: {new Date(member.joined_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Documentos Compartidos</CardTitle>
        </CardHeader>
        <CardContent>
          {resourcesLoading ? (
            <p className="text-muted-foreground">Cargando documentos compartidos...</p>
          ) : documents.length === 0 ? (
            <p className="text-muted-foreground">No hay documentos compartidos con este equipo.</p>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div key={doc.file_name} className="flex items-center justify-between p-2 border rounded-md">
                  <p>{doc.title || doc.file_name}</p>
                  <p className="text-muted-foreground">Compartido: {new Date(doc.shared_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Notas Compartidas</CardTitle>
        </CardHeader>
        <CardContent>
          {resourcesLoading ? (
            <p className="text-muted-foreground">Cargando notas compartidas...</p>
          ) : notes.length === 0 ? (
            <p className="text-muted-foreground">No hay notas compartidas con este equipo.</p>
          ) : (
            <div className="space-y-2">
              {notes.map((note) => (
                <div key={note.id} className="flex items-center justify-between p-2 border rounded-md">
                  <p>{note.title || "Sin título"}</p>
                  <p className="text-muted-foreground">Actualizado: {new Date(note.updated_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Member Dialog */}
      <Dialog open={addMemberOpen} onOpenChange={setAddMemberOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Añadir Miembro al Equipo {team.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>Ingresa el nombre de usuario de Telegram o correo electrónico del usuario que deseas añadir al equipo.</p>
            <Input
              placeholder="Nombre de usuario o correo electrónico"
              value={memberIdentifier}
              onChange={(e) => setMemberIdentifier(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setAddMemberOpen(false)}>Cancelar</Button>
              <Button onClick={handleAddMember} disabled={!memberIdentifier || searching}>{searching ? "Buscando..." : "Añadir"}</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Remove Member Dialog */}
      <Dialog open={removeMemberOpen} onOpenChange={setRemoveMemberOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Eliminar Miembro del Equipo {team.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p>Selecciona el miembro que deseas eliminar del equipo.</p>
            <div className="border rounded-md p-4 max-h-60 overflow-y-auto">
              {members.length > 0 ? (
                members.map((member) => (
                  <div key={member.account_id} className="flex items-center space-x-2 mb-2">
                    <input
                      type="radio"
                      id={`member-${member.account_id}`}
                      checked={selectedMember?.account_id === member.account_id}
                      onChange={() => setSelectedMember(member)}
                    />
                    <label htmlFor={`member-${member.account_id}`} className="flex-1">
                      ID de Cuenta: {member.account_id} {member.username ? `(${member.username})` : member.email ? `(${member.email})` : ''}
                    </label>
                  </div>
                ))
              ) : (
                <p className="text-muted-foreground">No hay miembros para eliminar.</p>
              )}
            </div>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setRemoveMemberOpen(false)}>Cancelar</Button>
              <Button onClick={handleRemoveMember} disabled={!selectedMember}>Eliminar</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
