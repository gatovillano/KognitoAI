export interface ContactProfile {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  tags: string[] | null;
  category: string | null;
  custom_fields: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}