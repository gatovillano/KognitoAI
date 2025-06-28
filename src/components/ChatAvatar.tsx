// ChatAvatar.tsx
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User } from 'lucide-react';

interface ChatAvatarProps {
  sender: 'user' | 'ai';
}

export const ChatAvatar: React.FC<ChatAvatarProps> = ({ sender }) => {
  if (sender === 'user') {
    return (
      <Avatar className="h-8 w-8">
        <AvatarFallback><User className="h-5 w-5" /></AvatarFallback>
      </Avatar>
    );
  } else {
    return (
      <Avatar className="h-16 w-16 border">
        <AvatarImage src="/logo-simple.png" alt="Kognito" />
        <AvatarFallback>K</AvatarFallback>
      </Avatar>
    );
  }
};
