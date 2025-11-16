"use client";

import { useState } from "react";
import type { Chatroom, Friend, Message, User } from "@/lib/data";
import { chatrooms as initialChatrooms, friends as initialFriends, loggedInUser } from "@/lib/data";
import { ChatSidebar } from "@/components/chat-sidebar";
import { ChatArea } from "@/components/chat-area";
import { MessageSquare } from "lucide-react";

export function ChitChatApp() {
  const [chatrooms, setChatrooms] = useState<Chatroom[]>(initialChatrooms);
  const [friends, setFriends] = useState<Friend[]>(initialFriends);
  const [selectedChat, setSelectedChat] = useState<Chatroom | null>(chatrooms[0]);

  const handleSelectChat = (chatroom: Chatroom) => {
    setSelectedChat(chatroom);
  };

  const handleCreateChatroom = (name: string, topic: string) => {
    const newChatroom: Chatroom = {
      id: `room-${Date.now()}`,
      name,
      topic,
      messages: [],
    };
    setChatrooms(prev => [...prev, newChatroom]);
    setSelectedChat(newChatroom);
  };

  const handleAddFriend = (friend: Friend) => {
    if (!friends.some(f => f.id === friend.id)) {
        setFriends(prev => [...prev, friend].sort((a, b) => a.name.localeCompare(b.name)));
    }
  };

  const handleRemoveFriend = (friendId: string) => {
    setFriends(prev => prev.filter(f => f.id !== friendId));
  };
  
  const handleSendMessage = (content: string) => {
    if (!selectedChat) return;

    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      content,
      sender: loggedInUser,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true }),
    };

    const updatedChatrooms = chatrooms.map(chatroom => {
      if (chatroom.id === selectedChat.id) {
        return {
          ...chatroom,
          messages: [...chatroom.messages, newMessage],
        };
      }
      return chatroom;
    });

    setChatrooms(updatedChatrooms);

    const updatedSelectedChat = updatedChatrooms.find(c => c.id === selectedChat.id);
    if (updatedSelectedChat) {
      setSelectedChat(updatedSelectedChat);
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background text-foreground">
      <ChatSidebar 
        chatrooms={chatrooms}
        friends={friends}
        selectedChat={selectedChat}
        onSelectChat={handleSelectChat}
        onCreateChatroom={handleCreateChatroom}
        onAddFriend={handleAddFriend}
        onRemoveFriend={handleRemoveFriend}
      />
      <main className="flex-1 flex flex-col">
        {selectedChat ? (
          <ChatArea 
            key={selectedChat.id} 
            selectedChat={selectedChat}
            onSendMessage={handleSendMessage}
          />
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-4">
            <MessageSquare className="w-24 h-24 text-muted-foreground/50" />
            <h2 className="mt-4 text-2xl font-semibold">Welcome to Chitter Chatter</h2>
            <p className="mt-2 text-muted-foreground">Select a chatroom to start messaging, or create a new one!</p>
          </div>
        )}
      </main>
    </div>
  );
}
