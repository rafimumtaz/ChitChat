"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Chatroom, Friend, Message, User } from "@/lib/data";
import { chatrooms as initialChatrooms, friends as initialFriends } from "@/lib/data";
import { ChatSidebar } from "@/components/chat-sidebar";
import { ChatArea } from "@/components/chat-area";
import { MessageSquare } from "lucide-react";

export function ChitChatApp() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [chatrooms, setChatrooms] = useState<Chatroom[]>(initialChatrooms);
  const [friends, setFriends] = useState<Friend[]>(initialFriends);
  const [selectedChat, setSelectedChat] = useState<Chatroom | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for logged in user in localStorage
    const storedUser = localStorage.getItem("user");
    if (!storedUser) {
      router.push("/login");
    } else {
      try {
        const parsedUser = JSON.parse(storedUser);
        // Map backend user structure to frontend User type if needed
        // Backend: { user_id, username, email, status }
        // Frontend: { id, name, avatarUrl, online }
        setUser({
            id: parsedUser.user_id.toString(),
            name: parsedUser.username,
            avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(parsedUser.username)}`,
            online: true
        });
        setLoading(false);
      } catch (e) {
        console.error("Failed to parse user data", e);
        router.push("/login");
      }
    }
  }, [router]);

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
    if (!selectedChat || !user) return;

    const newMessage: Message = {
      id: `msg-${Date.now()}`,
      content,
      sender: user,
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

  if (loading || !user) {
      return (
          <div className="flex h-screen w-full items-center justify-center bg-background text-foreground">
              Loading...
          </div>
      );
  }

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
        user={user}
      />
      <main className="flex-1 flex flex-col">
        {selectedChat ? (
          <ChatArea 
            key={selectedChat.id} 
            selectedChat={selectedChat}
            onSendMessage={handleSendMessage}
            currentUser={user}
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
