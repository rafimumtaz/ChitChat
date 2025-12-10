"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Chatroom, Friend, Message, User } from "@/lib/data";
import { friends as initialFriends } from "@/lib/data";
import { ChatSidebar } from "@/components/chat-sidebar";
import { ChatArea } from "@/components/chat-area";
import { MessageSquare } from "lucide-react";
import io from "socket.io-client";

// Use environment variable or default to localhost:5000
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
const socket = io(API_URL);

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

        // Fetch chatrooms and friends
        fetchChatrooms(currentUser.id);
        fetchFriends(currentUser.id);

        // Connect Socket
        socket.emit("join_user_room", { user_id: currentUser.id });

        // Listeners
        socket.on("new_message", (data: any) => {
            setChatrooms(prev => prev.map(c => {
                if (c.id === data.room_id) {
                    return { ...c, messages: [...c.messages, data] };
                }
                return c;
            }));

            // If current chat is the one receiving message, update it too (state is separate? no, derived mostly)
            // But setSelectedChat is separate state.
            setSelectedChat(prev => {
                if (prev && prev.id === data.room_id) {
                     return { ...prev, messages: [...prev.messages, data] };
                }
                return prev;
            });
        });

        socket.on("new_friend", (friend: Friend) => {
            setFriends(prev => {
                if (!prev.some(f => f.id === friend.id)) {
                    return [...prev, friend].sort((a, b) => a.name.localeCompare(b.name));
                }
                return prev;
            });
        });

        socket.on("added_to_room", (data: any) => {
             // Re-fetch chatrooms to get the new one
             fetchChatrooms(currentUser.id);
        });

        socket.on("new_private_chat", (data: any) => {
             fetchChatrooms(currentUser.id);
        });

        setLoading(false);

        return () => {
             socket.off("new_message");
             socket.off("new_friend");
             socket.off("added_to_room");
             socket.off("new_private_chat");
        }
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
              // Join sockets for these rooms
              data.data.forEach((room: Chatroom) => {
                   socket.emit("join_room", { room_id: room.id });
              });
          } else {
              console.error("Failed to fetch chatrooms");
          }
      } catch (error) {
          console.error("Error fetching chatrooms:", error);
      }
  };

  const fetchFriends = async (userId: string) => {
      try {
          const res = await fetch(`${API_URL}/friends?user_id=${userId}`);
          if (res.ok) {
              const data = await res.json();
              setFriends(data.data);
          } else {
              console.error("Failed to fetch friends");
          }
      } catch (error) {
          console.error("Error fetching friends:", error);
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
            // Join socket room
            socket.emit("join_room", { room_id: newChatroom.id });
        } else {
            console.error("Failed to create chatroom");
            alert("Failed to create chatroom");
        }
    } catch (error) {
        console.error("Error creating chatroom:", error);
        alert("Error creating chatroom");
    }
  };

  const handleAddFriend = async (friend: Friend) => {
    if (!user) return;

    // Optimistic update
    if (!friends.some(f => f.id === friend.id)) {
        setFriends(prev => [...prev, friend].sort((a, b) => a.name.localeCompare(b.name)));
    }

    try {
        const res = await fetch(`${API_URL}/friends`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: user.id,
                friend_id: friend.id
            }),
        });

        if (!res.ok) {
            console.error("Failed to add friend");
            // Revert if failed (optional, but good practice)
            setFriends(prev => prev.filter(f => f.id !== friend.id));
        }
    } catch (error) {
        console.error("Error adding friend:", error);
        setFriends(prev => prev.filter(f => f.id !== friend.id));
    }
  };

  const handleRemoveFriend = (friendId: string) => {
    setFriends(prev => prev.filter(f => f.id !== friendId));
  };

  const handleStartPrivateChat = async (friend: Friend) => {
    if (!user) return;

    try {
        const res = await fetch(`${API_URL}/private-chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: user.id,
                friend_id: friend.id
            }),
        });

        if (res.ok) {
            const data = await res.json();
            const roomData = data.data;

            // Backend returns technical room name, we want to show friend's name
            const newChatroom: Chatroom = {
                id: roomData.room_id.toString(),
                name: friend.name,
                topic: "Direct Message",
                messages: [],
                type: 'direct' // Assuming Chatroom interface has type optional or we ignore
            };

            // Check if room already in list
            const existing = chatrooms.find(c => c.id === newChatroom.id);
            if (existing) {
                handleSelectChat(existing);
            } else {
                setChatrooms(prev => [newChatroom, ...prev]);
                handleSelectChat(newChatroom);
                // Join socket room
                socket.emit("join_room", { room_id: newChatroom.id });
            }
        }
    } catch (error) {
        console.error("Error starting private chat", error);
    }
  };

  const handleAddMember = async (userId: string) => {
    if (!selectedChat) return;
    try {
        const res = await fetch(`${API_URL}/chatrooms/add-member`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_id: selectedChat.id,
                user_id: userId
            })
        });
        if (!res.ok) {
            console.error("Failed to add member");
            alert("Failed to add member");
        } else {
            alert("Member added successfully");
        }
    } catch (error) {
        console.error("Error adding member:", error);
    }
  };

  const handleSendMessage = (content: string) => {
    if (!selectedChat || !user) return;

    // Call API
    // We rely on socket 'new_message' event to update the UI to avoid duplicate bubbles
    // because the backend emits the event to sender as well.
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
        onStartPrivateChat={handleStartPrivateChat}
        user={user}
      />
      <main className="flex-1 flex flex-col">
        {selectedChat ? (
          <ChatArea 
            key={selectedChat.id} 
            selectedChat={selectedChat}
            onSendMessage={handleSendMessage}
            onAddMember={handleAddMember}
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
