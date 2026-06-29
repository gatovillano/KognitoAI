export interface SelectedContextItem {
  id: string;
  type: 'document' | 'collection' | 'repository' | 'image' | 'album' | string;
  name: string;
  title?: string;
  topic?: string;
  content?: string;
  file_name?: string;
}
