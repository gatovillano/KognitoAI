// ChatAvatar.tsx
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User, Bot } from 'lucide-react';

interface ChatAvatarProps {
  sender: 'user' | 'ai';
}

export const ChatAvatar: React.FC<ChatAvatarProps> = ({ sender }) => {
  return (
    <Avatar className="h-8 w-8">
      <AvatarFallback className={sender === 'user' ? 'bg-blue-500 text-white' : 'bg-primary text-primary-foreground'}>
        {sender === 'user' ? (
          <User className="h-4 w-4" />
        ) : (
          <Bot className="h-4 w-4" />
        )}
      </AvatarFallback>
    </Avatar>
  );
};
