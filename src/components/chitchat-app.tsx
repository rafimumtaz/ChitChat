"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Chatroom, Friend, Message, User } from "@/lib/data";
import { friends as initialFriends } from "@/lib/data";
import { ChatSidebar } from "@/components/chat-sidebar";
import { ChatArea } from "@/components/chat-area";
import { MessageSquare } from "lucide-react";

// Use environment variable or default to localhost:5000
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export function ChitChatApp() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [chatrooms, setChatrooms] = useState<Chatroom[]>([]);
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
        // Map backend user structure to frontend User type
        const currentUser = {
            id: parsedUser.user_id.toString(),
            name: parsedUser.username,
            avatarUrl: `https://ui-avatars.com/api/?name=${encodeURIComponent(parsedUser.username)}`,
            online: true
        };
        setUser(currentUser);

        // Fetch chatrooms
        fetchChatrooms(currentUser.id);

        setLoading(false);
      } catch (e) {
        console.error("Failed to parse user data", e);
        router.push("/login");
      }
    }
  }, [router]);

  const fetchChatrooms = async (userId: string) => {
      try {
          const res = await fetch(`${API_URL}/chatrooms?user_id=${userId}`);
          if (res.ok) {
              const data = await res.json();
              setChatrooms(data.data);
          } else {
              console.error("Failed to fetch chatrooms");
          }
      } catch (error) {
          console.error("Error fetching chatrooms:", error);
      }
  };

  const handleSelectChat = async (chatroom: Chatroom) => {
    // Optimistically set selected chat (will show empty messages initially)
    // or keep previous selectedChat until data loads.
    // For better UX, we'll set it immediately and then fetch messages.
    setSelectedChat(chatroom);

    try {
        const res = await fetch(`${API_URL}/messages?room_id=${chatroom.id}`);
        if (res.ok) {
            const data = await res.json();
            const fullChatroom = {
                ...chatroom,
                messages: data.data
            };
            setSelectedChat(fullChatroom);

            // Also update the chatrooms list cache so if we switch back and forth it might persist (optional)
            setChatrooms(prev => prev.map(c => c.id === chatroom.id ? fullChatroom : c));
        } else {
             console.error("Failed to fetch messages");
        }
    } catch (error) {
        console.error("Error fetching messages:", error);
    }
  };

  const handleCreateChatroom = async (name: string, topic: string) => {
    if (!user) return;

    try {
        const res = await fetch(`${API_URL}/create-room`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                room_name: name,
                created_by: user.id
            }),
        });

        if (res.ok) {
            const data = await res.json();
            const newChatroom: Chatroom = {
                id: data.data.room_id.toString(),
                name: data.data.room_name,
                topic: topic || "General topic",
                messages: [],
            };
            setChatrooms(prev => [...prev, newChatroom]);
            setSelectedChat(newChatroom);
        } else {
            console.error("Failed to create chatroom");
            alert("Failed to create chatroom");
        }
    } catch (error) {
        console.error("Error creating chatroom:", error);
        alert("Error creating chatroom");
    }
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

    // Send to backend
    // Note: This logic was already here, but in the previous turn I only implemented "create room".
    // I should also hook this up to the backend if requested, but the task is specific to "Create Chatroom".
    // However, since the user asked to "fix and implement Create Chatroom", I'll stick to that.
    // But for better UX, I'll keep the optimistic update locally, and maybe later hook it up.
    // The previous prompt said "Publisher... Create a function that publishes... when a user sends a message via the API".
    // So I should probably call the API here too?
    // The user said "Goal: The 'Create Chatroom' button must work immediately...".
    // I will focus on Create Chatroom.

    // Optimistic update
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

    // Call API (Background)
    fetch(`${API_URL}/send-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            sender_id: user.id,
            room_id: selectedChat.id,
            content: content
        })
    }).catch(err => console.error("Failed to send message", err));
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
