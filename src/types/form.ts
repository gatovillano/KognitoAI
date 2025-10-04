export type FieldType = 'text' | 'textarea' | 'checkbox' | 'radio' | 'select';

export interface FormFieldData {
  id: string;
  label: string;
  description?: string; // Nueva propiedad para la descripción de la pregunta
  type: FieldType;
  is_required: boolean;
  options?: string[];
}

export interface FormSectionData {
  id: string;
  title: string;
  description?: string;
  elements: FormElement[]; // Las secciones pueden contener campos o subsecciones
}

export type FormElement = FormFieldData | FormSectionData;

export interface Form {
  id: string;
  title: string;
  description?: string;
  user_id: string;
  elements: FormElement[];
}

export interface FormResponseAnswer {
  field_id: string;
  value: any;
}

export interface FormResponse {
  id: string;
  form_id: string;
  submitted_at: string;
  answers: FormResponseAnswer[];
  contact_profile_id?: string;
  contact_profile_name?: string;
}

export interface LinkedFormResponse {
  id: string;
  form_id: string;
  form_title: string;
  submitted_at: string;
  answers: Record<string, any>;
}
