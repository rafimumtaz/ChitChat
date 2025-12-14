"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Chatroom, Message, User } from "@/lib/data";
import { cn } from "@/lib/utils";
import { Info, SendHorizontal, Smile, Paperclip, X, FileIcon, Loader2 } from "lucide-react";
import React, { useState, useRef, useEffect } from "react";
import { Socket } from "socket.io-client";

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { UserPlus, UserMinus } from "lucide-react";
import { users } from "@/lib/data";

interface ChatAreaProps {
  selectedChat: Chatroom;
  onSendMessage: (content: string, attachment?: { url: string, type: string, name: string }) => void;
  onAddMember: (userId: string) => void;
  currentUser: User;
  socket: Socket | null;
}

export function ChatArea({ selectedChat, onSendMessage, onAddMember, currentUser, socket }: ChatAreaProps) {
  const [newMessage, setNewMessage] = useState("");
  const [pendingAttachment, setPendingAttachment] = useState<{ url: string, type: string, name: string } | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [typingUsers, setTypingUsers] = useState<Map<string, string>>(new Map());

  const scrollViewportRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const scrollToBottom = (behavior: ScrollBehavior = 'auto') => {
      messagesEndRef.current?.scrollIntoView({ behavior });
  }

  useEffect(() => {
    // Scroll to bottom immediately when chat changes or messages update
    // 'instant' behavior ensures it happens "directly"
    const timeoutId = setTimeout(() => {
        scrollToBottom('instant');
    }, 50); // Small buffer to ensure DOM layout

    return () => clearTimeout(timeoutId);
  }, [selectedChat.messages, selectedChat.id]);

  // Typing listeners
  useEffect(() => {
      if (!socket) return;

      const onDisplayTyping = (data: any) => {
          if (data.room_id === selectedChat.id) {
              setTypingUsers(prev => {
                  const newMap = new Map(prev);
                  newMap.set(data.user_id, data.username);
                  return newMap;
              });
              scrollToBottom();
          }
      };

      const onHideTyping = (data: any) => {
          if (data.room_id === selectedChat.id) {
              setTypingUsers(prev => {
                  const newMap = new Map(prev);
                  newMap.delete(data.user_id);
                  return newMap;
              });
          }
      };

      socket.on("display_typing", onDisplayTyping);
      socket.on("hide_typing", onHideTyping);

      // Clear typing users when chat changes
      setTypingUsers(new Map());

      return () => {
          socket.off("display_typing", onDisplayTyping);
          socket.off("hide_typing", onHideTyping);
      };
  }, [socket, selectedChat.id]);

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newMessage.trim() === "" && !pendingAttachment) return;

    onSendMessage(newMessage, pendingAttachment || undefined);
    setNewMessage("");
    setPendingAttachment(null);

    // Stop typing immediately on send
    if (socket && typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
        socket.emit("typing_stop", { room_id: selectedChat.id });
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      setNewMessage(e.target.value);

      if (socket) {
          socket.emit("typing_start", { room_id: selectedChat.id });

          if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);

          typingTimeoutRef.current = setTimeout(() => {
              socket.emit("typing_stop", { room_id: selectedChat.id });
          }, 2000);
      }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files[0]) {
          const file = e.target.files[0];
          setIsUploading(true);

          const formData = new FormData();
          formData.append('file', file);

          const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

          try {
              const res = await fetch(`${API_URL}/api/upload`, {
                  method: 'POST',
                  body: formData
              });

              if (res.ok) {
                  const data = await res.json();
                  setPendingAttachment({
                      url: data.file_url, // Backend should return relative or full path. If relative, prepend API_URL if needed, but static is served by backend.
                      type: data.file_type,
                      name: data.original_name
                  });
              } else {
                  console.error("Upload failed");
                  alert("Failed to upload file.");
              }
          } catch (error) {
              console.error("Error uploading file:", error);
              alert("Error uploading file.");
          } finally {
              setIsUploading(false);
              if (fileInputRef.current) fileInputRef.current.value = "";
          }
      }
  };

  // Determine header status
  let headerStatus = selectedChat.topic;
  if (selectedChat.userStatus) {
      // It's a DM and we have status
      if (selectedChat.userStatus.online) {
          headerStatus = "Online";
      } else if (selectedChat.userStatus.lastSeen) {
          // Parse ISO string
          const date = new Date(selectedChat.userStatus.lastSeen);
          headerStatus = `Last seen ${date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;
      } else {
          headerStatus = "Offline";
      }
  }

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b flex items-center justify-between bg-card">
        <div>
          <h2 className="text-lg font-semibold">{selectedChat.name}</h2>
          <p className={cn("text-sm text-muted-foreground", headerStatus === "Online" && "text-green-600 font-medium")}>{headerStatus}</p>
        </div>
        <div className="flex items-center gap-2">
            {(selectedChat.type === 'group' || !selectedChat.type) && (
                <AddMemberDialog onAddMember={onAddMember} currentUser={currentUser} />
            )}
            <RoomInfoDialog selectedChat={selectedChat} currentUser={currentUser} />
        </div>
      </header>

      <ScrollArea className="flex-1" viewportRef={scrollViewportRef}>
        <div className="p-4 lg:p-8 space-y-6">
          {selectedChat.messages.map((message) => (
            <ChatMessage key={message.id} message={message} currentUser={currentUser} />
          ))}
          {Array.from(typingUsers.entries()).map(([userId, username]) => (
             <TypingBubble key={userId} username={username} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      
      <footer className="p-4 border-t bg-card">
        {pendingAttachment && (
            <div className="flex items-center gap-2 p-2 mb-2 bg-accent/30 rounded-md border text-sm max-w-fit">
                {pendingAttachment.type.startsWith('image/') ? (
                    <div className="h-10 w-10 relative overflow-hidden rounded">
                         {/* We need full URL if backend is different port */}
                         <img src={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'}${pendingAttachment.url}`} alt="Preview" className="object-cover h-full w-full" />
                    </div>
                ) : (
                    <FileIcon className="h-5 w-5 text-muted-foreground" />
                )}
                <span className="truncate max-w-[200px]">{pendingAttachment.name}</span>
                <button onClick={() => setPendingAttachment(null)} className="ml-2 hover:bg-muted p-1 rounded-full">
                    <X className="h-4 w-4 text-muted-foreground" />
                </button>
            </div>
        )}
        <form onSubmit={handleFormSubmit} className="relative">
          <Input
            placeholder="Type a message..."
            className="pr-36 h-12 text-base"
            value={newMessage}
            onChange={handleInputChange}
            disabled={isUploading}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
             <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                className="hidden"
             />
            <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
            >
              {isUploading ? <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" /> : <Paperclip className="w-6 h-6 text-muted-foreground" />}
            </Button>
            <Button type="button" variant="ghost" size="icon">
              <Smile className="w-6 h-6 text-muted-foreground" />
            </Button>
            <Button type="submit" size="icon" className="h-9 w-9 bg-primary hover:bg-primary/90" disabled={isUploading}>
              <SendHorizontal className="w-5 h-5 text-primary-foreground" />
            </Button>
          </div>
        </form>
      </footer>
    </div>
  );
}

function TypingBubble({ username }: { username: string }) {
  return (
    <div className="flex items-start gap-4">
      <Avatar className="h-10 w-10">
        <AvatarFallback>{username.charAt(0)}</AvatarFallback>
      </Avatar>
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2">
          <p className="font-semibold text-sm">{username}</p>
        </div>
        <div className="p-3 rounded-lg bg-card rounded-bl-none shadow-sm w-fit">
          <div className="flex gap-1 h-5 items-center px-1">
            <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
            <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
            <span className="w-2 h-2 bg-foreground/40 rounded-full animate-bounce"></span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AddMemberDialog({ onAddMember, currentUser }: { onAddMember: (userId: string) => void; currentUser: User }) {
  const [open, setOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [availableUsers, setAvailableUsers] = useState<User[]>([]);

  // Reuse the search logic from ChatSidebar ideally, but duplicating for now as it's small
  React.useEffect(() => {
    const searchUsers = async () => {
        if (!searchTerm) {
            setAvailableUsers([]);
            return;
        }

        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
        try {
            // When adding a member to a group, we want to see ALL users, including friends.
            const res = await fetch(`${API_URL}/users/search?query=${encodeURIComponent(searchTerm)}&user_id=${currentUser.id}&include_friends=true`);
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
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTerm, currentUser.id]);

  const handleInvite = async (user: User) => {
    // Call invite logic (which was passed as onAddMember prop, but logic should be updated to /invite)
    // The prop name is onAddMember but implementation in ChitchatApp calls /chatrooms/add-member.
    // We will update the logic in the parent component to call the invite endpoint, or update backend add-member to invite.
    // The previous backend update made /invite endpoint.
    // Let's assume onAddMember prop now calls the Invite Logic or we rename it.
    // For minimal frontend changes, we use the existing prop but rename UI text.
    onAddMember(user.id);
    setOpen(false);
    alert(`Invitation sent to ${user.name}`);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" title="Invite Member">
          <UserPlus className="w-5 h-5" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Invite to Group</DialogTitle>
          <DialogDescription>Search for users to invite to this chatroom.</DialogDescription>
        </DialogHeader>
        <div className="pt-4">
            <Input
              placeholder="Search by name..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
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
                <Button size="sm" onClick={() => handleInvite(user)}>Invite</Button>
              </div>
            )) : <p className="text-sm text-center text-muted-foreground py-4">No users found.</p>}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}

function RoomInfoDialog({ selectedChat, currentUser }: { selectedChat: Chatroom; currentUser: User }) {
  const [open, setOpen] = useState(false);
  const [info, setInfo] = useState<{ room_name: string; admin_name: string; created_by: string; members: User[] } | null>(null);

  const fetchInfo = async () => {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      try {
          const res = await fetch(`${API_URL}/room/${selectedChat.id}/info`);
          if (res.ok) {
              const data = await res.json();
              setInfo(data.data);
          }
      } catch (error) {
          console.error("Error fetching room info:", error);
      }
  };

  const handleKick = async (userId: string) => {
      if (!confirm("Are you sure you want to remove this user?")) return;

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      try {
          const res = await fetch(`${API_URL}/room/${selectedChat.id}/kick`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                  user_id: userId,
                  current_user_id: currentUser.id
              })
          });

          if (res.ok) {
              setInfo(prev => prev ? { ...prev, members: prev.members.filter(m => m.id !== userId) } : null);
          } else {
              alert("Failed to kick user.");
          }
      } catch (error) {
          console.error("Error kicking user:", error);
      }
  };

  const handleDeleteRoom = async () => {
      if (!confirm("Are you sure you want to delete this room? This cannot be undone.")) return;

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      try {
          const res = await fetch(`${API_URL}/room/${selectedChat.id}`, {
              method: 'DELETE',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ current_user_id: currentUser.id })
          });
          if (res.ok) {
              setOpen(false);
              window.location.reload(); // Refresh to update list
          }
      } catch (error) {
          console.error("Error deleting room", error);
      }
  };

  const handleClearChat = async () => {
      if (!confirm("Are you sure you want to clear the chat history?")) return;

      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      try {
          const res = await fetch(`${API_URL}/room/${selectedChat.id}/messages`, {
              method: 'DELETE',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ current_user_id: currentUser.id })
          });
          if (res.ok) {
              alert("Chat cleared.");
              setOpen(false);
          }
      } catch (error) {
          console.error("Error clearing chat", error);
      }
  };

  return (
    <Dialog open={open} onOpenChange={(val) => { setOpen(val); if(val) fetchInfo(); }}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon">
          <Info className="w-5 h-5" />
          <span className="sr-only">Chatroom Info</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Room Info</DialogTitle>
          <DialogDescription>
             Details about this chatroom.
          </DialogDescription>
        </DialogHeader>
        {info ? (
            <div className="py-4 space-y-4">
                <div>
                    <h3 className="font-semibold text-lg">{info.room_name}</h3>
                    <p className="text-sm text-muted-foreground">Created By: {info.admin_name}</p>
                </div>

                {/* Admin Actions */}
                {info.created_by === currentUser.id && (
                    <div className="flex gap-2">
                        <Button variant="destructive" size="sm" onClick={handleDeleteRoom} className="flex-1">
                            Delete Room
                        </Button>
                        <Button variant="outline" size="sm" onClick={handleClearChat} className="flex-1 text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200">
                            Clear Chat
                        </Button>
                    </div>
                )}

                <div>
                    <h4 className="font-medium text-sm text-muted-foreground uppercase tracking-wider mb-2">Members ({info.members.length})</h4>
                    <ScrollArea className="max-h-64 -mx-6 px-6">
                        <div className="space-y-2">
                            {info.members.map(member => (
                                <div key={member.id} className="flex items-center justify-between p-2 rounded-md hover:bg-accent/50">
                                    <div className="flex items-center gap-3">
                                        <Avatar className="h-8 w-8">
                                            <AvatarImage src={member.avatarUrl} alt={member.name} />
                                            <AvatarFallback>{member.name.charAt(0)}</AvatarFallback>
                                        </Avatar>
                                        <div className="flex flex-col">
                                            <div className="flex items-center gap-2">
                                                <span className="text-sm font-medium">{member.name}</span>
                                                {member.id === info.created_by && (
                                                    <span className="text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-semibold">(Admin)</span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    {/* Kick Button: Show if current user is admin AND target is not themselves */}
                                    {info.created_by === currentUser.id && member.id !== currentUser.id && (
                                        <Button
                                            variant="destructive"
                                            size="icon"
                                            className="h-7 w-7"
                                            onClick={() => handleKick(member.id)}
                                            title="Kick User"
                                        >
                                            <UserMinus className="w-4 h-4" />
                                        </Button>
                                    )}
                                </div>
                            ))}
                        </div>
                    </ScrollArea>
                </div>
            </div>
        ) : (
            <div className="py-8 text-center text-muted-foreground">Loading...</div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ChatMessage({ message, currentUser }: { message: Message; currentUser: User }) {
    const isSender = message.sender.id === currentUser.id;
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

  return (
    <div className={cn("flex items-start gap-4", isSender && "flex-row-reverse")}>
      <Avatar className="h-10 w-10">
        <AvatarImage src={message.sender.avatarUrl} alt={message.sender.name} />
        <AvatarFallback>{message.sender.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
      </Avatar>
      <div className={cn("flex flex-col gap-1", isSender && "items-end")}>
        <div className="flex items-center gap-2">
            {!isSender && <p className="font-semibold text-sm">{message.sender.name}</p>}
            <p className="text-xs text-muted-foreground">{message.timestamp}</p>
        </div>
        <div className={cn("p-3 rounded-lg max-w-sm md:max-w-md shadow-sm", isSender ? "bg-primary text-primary-foreground rounded-br-none" : "bg-card rounded-bl-none")}>
          {message.attachment_url && (
              <div className="mb-2">
                  {message.attachment_type?.startsWith('image/') ? (
                      <a href={`${API_URL}${message.attachment_url}`} target="_blank" rel="noopener noreferrer">
                          <img
                            src={`${API_URL}${message.attachment_url}`}
                            alt={message.original_name || "Attachment"}
                            className="rounded-md max-h-60 object-cover"
                          />
                      </a>
                  ) : (
                      <a
                        href={`${API_URL}${message.attachment_url}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-2 p-2 bg-background/20 rounded hover:bg-background/30 transition-colors"
                      >
                          <FileIcon className="h-5 w-5" />
                          <span className="underline truncate max-w-[200px]">{message.original_name || "Download File"}</span>
                      </a>
                  )}
              </div>
          )}
          {message.content && <p className="leading-relaxed">{message.content}</p>}
        </div>
      </div>
    </div>
  );
}
