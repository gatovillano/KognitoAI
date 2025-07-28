// src/components/UploadProgressIndicator.tsx
import { Clock, Loader2, CheckCircle, XCircle, Upload } from 'lucide-react';

interface UploadTask {
  id: string;
  file_names: string[];
  topic: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  error_message?: string;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'pending':
      return <Clock className="h-4 w-4 text-yellow-500" />;
    case 'processing':
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    default:
      return <Upload className="h-4 w-4 text-gray-500" />;
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'pending':
      return 'En cola';
    case 'processing':
      return 'Procesando';
    case 'completed':
      return 'Completado';
    case 'failed':
      return 'Error';
    default:
      return 'Desconocido';
  }
};

interface UploadProgressIndicatorProps {
  tasks: UploadTask[];
}

const UploadProgressIndicator: React.FC<UploadProgressIndicatorProps> = ({ tasks }) => {
  if (tasks.length === 0) {
    return null;
  }

  return (
    <div className="mb-4">
      <div className="border-l-4 border-l-blue-500 bg-blue-50/50 dark:bg-blue-950/20 rounded-md p-4">
        <h3 className="text-lg font-semibold mb-2">Subiendo Documentos</h3>
        <ul>
          {tasks.map((task) => (
            <li key={task.id} className="flex items-center justify-between py-2">
              <div className="flex items-center">
                {getStatusIcon(task.status)}
                <span className="ml-2">{task.file_names[0]}</span>
              </div>
              <span className="text-sm text-muted-foreground">{getStatusText(task.status)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default UploadProgressIndicator;
