"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { Chatroom, Message, User } from "@/lib/data";
import { cn } from "@/lib/utils";
import { Info, SendHorizontal, Smile } from "lucide-react";
import React, { useState, useRef, useEffect } from "react";

interface ChatAreaProps {
  selectedChat: Chatroom;
  onSendMessage: (content: string) => void;
  currentUser: User;
}

export function ChatArea({ selectedChat, onSendMessage, currentUser }: ChatAreaProps) {
  const [newMessage, setNewMessage] = useState("");
  const scrollViewportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollViewportRef.current) {
        scrollViewportRef.current.scrollTop = scrollViewportRef.current.scrollHeight;
    }
  }, [selectedChat.messages]);


  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newMessage.trim() === "") return;

    onSendMessage(newMessage);
    setNewMessage("");
  };

  return (
    <div className="flex flex-col h-full">
      <header className="p-4 border-b flex items-center justify-between bg-card">
        <div>
          <h2 className="text-lg font-semibold">{selectedChat.name}</h2>
          <p className="text-sm text-muted-foreground">{selectedChat.topic}</p>
        </div>
        <Button variant="ghost" size="icon">
          <Info className="w-5 h-5" />
          <span className="sr-only">Chatroom Info</span>
        </Button>
      </header>

      <ScrollArea className="flex-1" viewportref={scrollViewportRef}>
        <div className="p-4 lg:p-8 space-y-6">
          {selectedChat.messages.map((message) => (
            <ChatMessage key={message.id} message={message} currentUser={currentUser} />
          ))}
        </div>
      </ScrollArea>
      
      <footer className="p-4 border-t bg-card">
        <form onSubmit={handleFormSubmit} className="relative">
          <Input
            placeholder="Type a message..."
            className="pr-28 h-12 text-base"
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
          />
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center">
            <Button type="button" variant="ghost" size="icon">
              <Smile className="w-6 h-6 text-muted-foreground" />
            </Button>
            <Button type="submit" size="icon" className="h-9 w-9 bg-primary hover:bg-primary/90">
              <SendHorizontal className="w-5 h-5 text-primary-foreground" />
            </Button>
          </div>
        </form>
      </footer>
    </div>
  );
}

function ChatMessage({ message, currentUser }: { message: Message; currentUser: User }) {
    const isSender = message.sender.id === currentUser.id;
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
          <p className="leading-relaxed">{message.content}</p>
        </div>
      </div>
    </div>
  );
}
