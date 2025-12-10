"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import type { Chatroom, Friend, User } from "@/lib/data";
import { users } from "@/lib/data";
import { Hash, MessageSquare, Plus, Search, Users, UserPlus, X } from "lucide-react";
import { UserNav } from "./user-nav";
import React, { useMemo, useState } from "react";

interface ChatSidebarProps {
  chatrooms: Chatroom[];
  friends: Friend[];
  selectedChat: Chatroom | null;
  onSelectChat: (chatroom: Chatroom) => void;
  onCreateChatroom: (name: string, topic: string) => void;
  onAddFriend: (friend: User) => void;
  onRemoveFriend: (friendId: string) => void;
  onStartPrivateChat: (friend: Friend) => void;
  user: User;
}

export function ChatSidebar({
  chatrooms,
  friends,
  selectedChat,
  onSelectChat,
  onCreateChatroom,
  onAddFriend,
  onRemoveFriend,
  onStartPrivateChat,
  user
}: ChatSidebarProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredChatrooms = useMemo(() => 
    chatrooms.filter(room => room.name.toLowerCase().includes(searchTerm.toLowerCase())),
    [chatrooms, searchTerm]
  );
  
  const filteredFriends = useMemo(() =>
    friends.filter(friend => friend.name.toLowerCase().includes(searchTerm.toLowerCase())),
    [friends, searchTerm]
  );

  return (
    <div className="flex flex-col h-full bg-card border-r w-80">
      <div className="p-4 border-b flex justify-between items-center">
        <div className="flex items-center gap-2">
            <MessageSquare className="w-8 h-8 text-primary" />
            <h1 className="text-xl font-bold">Chitter Chatter</h1>
        </div>
        <UserNav user={user} />
      </div>
      <div className="p-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
          <Input 
            placeholder="Search..." 
            className="pl-10"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4 pt-0 space-y-6">
          <NavSection
            title="Chatrooms"
            icon={<Hash className="w-4 h-4" />}
            action={<CreateChatroomDialog onCreateChatroom={onCreateChatroom} />}
          >
            {filteredChatrooms.map((room) => (
              <NavItem
                key={room.id}
                item={room}
                isSelected={selectedChat?.id === room.id}
                onClick={() => onSelectChat(room)}
                icon={<Hash className="w-4 h-4 text-muted-foreground" />}
              />
            ))}
          </NavSection>

          <NavSection
            title="Friends"
            icon={<Users className="w-4 h-4" />}
            action={<AddFriendDialog onAddFriend={onAddFriend} currentFriends={friends} currentUser={user} />}
          >
            {filteredFriends.map((friend) => (
              <FriendItem key={friend.id} friend={friend} onRemoveFriend={onRemoveFriend} onStartPrivateChat={onStartPrivateChat} />
            ))}
          </NavSection>
        </div>
      </ScrollArea>
      <div className="p-4 border-t flex items-center gap-3">
         <Avatar className="h-10 w-10 border-2 border-primary">
            <AvatarImage src={user.avatarUrl} alt={user.name} />
            <AvatarFallback>{user.name.charAt(0)}</AvatarFallback>
         </Avatar>
         <div className="flex-1">
            <p className="font-semibold">{user.name}</p>
            <p className="text-sm text-muted-foreground">Online</p>
         </div>
      </div>
    </div>
  );
}


function NavSection({ title, icon, action, children }: { title: string, icon: React.ReactNode, action: React.ReactNode, children: React.ReactNode }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {icon}
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">{title}</h2>
        </div>
        {action}
      </div>
      <ul className="space-y-1">
        {children}
      </ul>
    </div>
  )
}

function NavItem({ item, isSelected, onClick, icon }: { item: Chatroom, isSelected: boolean, onClick: () => void, icon: React.ReactNode }) {
  return (
    <li>
      <Button
        variant="ghost"
        className={cn(
          "w-full justify-start gap-2 transition-colors",
          isSelected && "bg-accent text-accent-foreground"
        )}
        onClick={onClick}
      >
        {icon}
        <span className="flex-1 truncate text-left">{item.name}</span>
      </Button>
    </li>
  );
}

function FriendItem({ friend, onRemoveFriend, onStartPrivateChat }: { friend: Friend, onRemoveFriend: (friendId: string) => void, onStartPrivateChat: (friend: Friend) => void }) {
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <li 
      className="w-full rounded-md transition-colors hover:bg-accent/50 cursor-pointer"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onStartPrivateChat(friend)}
    >
       <div className="flex items-center w-full justify-start gap-3 h-12 px-2">
        <div className="relative">
          <Avatar className="h-8 w-8">
            <AvatarImage src={friend.avatarUrl} alt={friend.name} />
            <AvatarFallback>{friend.name.charAt(0)}</AvatarFallback>
          </Avatar>
          {friend.online && <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 rounded-full border-2 border-card" />}
        </div>
        <span className="flex-1 truncate text-left">{friend.name}</span>
        {isHovered && (
          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onStartPrivateChat(friend)}>
                    <MessageSquare className="w-4 h-4 text-muted-foreground" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Message</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => onRemoveFriend(friend.id)}>
                    <X className="w-4 h-4 text-muted-foreground" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Remove Friend</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        )}
      </div>
    </li>
  )
}

function CreateChatroomDialog({ onCreateChatroom }: { onCreateChatroom: (name: string, topic: string) => void }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [topic, setTopic] = useState("");

  const handleCreate = () => {
    if (name.trim()) {
      const finalName = name.startsWith('#') ? name : `#${name.replace(/\s+/g, '-').toLowerCase()}`;
      onCreateChatroom(finalName, topic || `A new chatroom: ${finalName}`);
      setName("");
      setTopic("");
      setOpen(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7" id="create-chatroom-trigger">
                <Plus className="w-4 h-4" />
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>
            <p>Create Chatroom</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Create Chatroom</DialogTitle>
          <DialogDescription>
            Give your new chatroom a name and a topic to get started.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="name" className="text-right">
              Name
            </Label>
            <Input id="name" placeholder="#project-z" className="col-span-3" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid grid-cols-4 items-center gap-4">
            <Label htmlFor="topic" className="text-right">
              Topic
            </Label>
            <Input id="topic" placeholder="Planning the next big thing." className="col-span-3" value={topic} onChange={(e) => setTopic(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleCreate} id="create-chatroom-submit">Create</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddFriendDialog({ onAddFriend, currentFriends, currentUser }: { onAddFriend: (user: User) => void; currentFriends: Friend[]; currentUser: User }) {
  const [open, setOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);

  // Search users via API when searchTerm changes
  React.useEffect(() => {
    const searchUsers = async () => {
        if (!searchTerm) {
            setAvailableUsers([]);
            return;
        }

        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
        try {
            const res = await fetch(`${API_URL}/users/search?query=${encodeURIComponent(searchTerm)}&user_id=${currentUser.id}`);
            if (res.ok) {
                const data = await res.json();
                setAvailableUsers(data.data);
            }
        } catch (error) {
            console.error("Error searching users", error);
        }
    };

    const timeoutId = setTimeout(() => {
        searchUsers();
    }, 300); // Debounce

    return () => clearTimeout(timeoutId);
  }, [searchTerm, currentUser.id]);


  const handleAdd = (user: User) => {
    onAddFriend(user);
    // Remove from local state immediately to reflect UI change
    setAvailableUsers(prev => prev.filter(u => u.id !== user.id));
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <DialogTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7">
                <UserPlus className="w-4 h-4" />
              </Button>
            </DialogTrigger>
          </TooltipTrigger>
          <TooltipContent>
            <p>Add Friend</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Add a Friend</DialogTitle>
          <DialogDescription>Search for users to add to your friends list.</DialogDescription>
        </DialogHeader>
        <div className="pt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input 
              placeholder="Search by name..."
              className="pl-9"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        <ScrollArea className="max-h-64 -mx-6 px-6">
          <div className="space-y-2 py-4">
            {availableUsers.length > 0 ? availableUsers.map(user => (
              <div key={user.id} className="flex items-center justify-between p-2 rounded-md hover:bg-accent">
                <div className="flex items-center gap-3">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={user.avatarUrl} alt={user.name} />
                    <AvatarFallback>{user.name.charAt(0)}</AvatarFallback>
                  </Avatar>
                  <span>{user.name}</span>
                </div>
                <Button size="sm" onClick={() => handleAdd(user)}>Add</Button>
              </div>
            )) : <p className="text-sm text-center text-muted-foreground py-4">No users found or all users are friends.</p>}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
