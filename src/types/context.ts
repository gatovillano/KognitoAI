export interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection' | 'onlyoffice' | 'repository' | 'image' | 'album' | string;
  name: string;
  title?: string;
  topic?: string;
  content?: string;
  file_name?: string;
  doc_source?: 'rag' | 'onlyoffice' | string;
}
