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
      <Avatar className="h-16 w-16">
        <AvatarImage src="/logo-simple.png" alt="Kognito" style={{ width: '90%', height: '90%', objectFit: 'contain' }} />
        <AvatarFallback>K</AvatarFallback>
      </Avatar>
    );
  }
};
