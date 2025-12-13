"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import type { Chatroom, Friend, Message, User } from "@/lib/data";
import { friends as initialFriends } from "@/lib/data";
import { ChatSidebar } from "@/components/chat-sidebar";
import { ChatArea } from "@/components/chat-area";
import { MessageSquare } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { io, Socket } from "socket.io-client";

// Use environment variable or default to localhost:5000
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export function ChitChatApp() {
  const { toast } = useToast();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);
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

        // Initialize Socket with user_id
        const newSocket = io(API_URL, {
            query: { user_id: currentUser.id }
        });
        setSocket(newSocket);

        // Handle window unload
        const handleBeforeUnload = () => newSocket.disconnect();
        window.addEventListener('beforeunload', handleBeforeUnload);

        setLoading(false);

        return () => {
            newSocket.disconnect();
            window.removeEventListener('beforeunload', handleBeforeUnload);
        };
      } catch (e) {
        console.error("Failed to parse user data", e);
        router.push("/login");
      }
    }
  }, [router]);

  // Socket Listeners
  useEffect(() => {
      if (!socket || !user) return;

      // Join user room
      socket.emit("join_user_room", { user_id: user.id });

      socket.on("user_status_change", (data: any) => {
          setFriends(prev => prev.map(f => {
              if (f.id === data.user_id) {
                  return { ...f, online: data.status === 'online', lastSeen: data.last_seen };
              }
              return f;
          }));

          setSelectedChat(prev => {
              if (prev && prev.otherUserId === data.user_id) {
                  return { ...prev, userStatus: { online: data.status === 'online', lastSeen: data.last_seen } };
              }
              return prev;
          });
      });

      socket.on("new_message", (data: any) => {
            setChatrooms(prev => prev.map(c => {
                if (c.id === data.room_id) {
                    return { ...c, messages: [...c.messages, data] };
                }
                return c;
            }));

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

        socket.on("new_notification", (data: any) => {
             toast({
                 title: "New Notification",
                 description: data.message,
             });
        });

        socket.on("update_data", (data: any) => {
             if (data.event === 'FRIEND_ACCEPTED') {
                 const friend = data.friend;
                 setFriends(prev => {
                    if (!prev.some(f => f.id === friend.id)) {
                        return [...prev, friend].sort((a, b) => a.name.localeCompare(b.name));
                    }
                    return prev;
                 });
                 toast({
                     title: "Friend Added",
                     description: `You are now friends with ${friend.name}.`,
                 });
             } else if (data.event === 'GROUP_JOINED') {
                 fetchChatrooms(user.id);
                 toast({
                     title: "Joined Group",
                     description: "You have been added to a new chatroom.",
                 });
             } else if (data.event === 'GROUP_INVITE_ACCEPTED') {
                 fetchChatrooms(user.id);
                 toast({
                     title: "Invitation Accepted",
                     description: `${data.acceptor_name} joined the group.`,
                 });
             }
        });

        socket.on("added_to_room", (data: any) => {
             fetchChatrooms(user.id);
        });

        socket.on("new_private_chat", (data: any) => {
             fetchChatrooms(user.id);
        });

        socket.on("room_deleted", (data: any) => {
             setChatrooms(prev => prev.filter(c => c.id !== data.room_id));
             setSelectedChat(prev => {
                 if (prev && prev.id === data.room_id) {
                     return null;
                 }
                 return prev;
             });
             toast({
                 title: "Room Deleted",
                 description: "The chatroom has been deleted by the admin.",
                 variant: "destructive"
             });
        });

        socket.on("chat_cleared", (data: any) => {
             setSelectedChat(prev => {
                 if (prev && prev.id === data.room_id) {
                     return { ...prev, messages: [] };
                 }
                 return prev;
             });
             setChatrooms(prev => prev.map(c => {
                 if (c.id === data.room_id) {
                     return { ...c, messages: [] };
                 }
                 return c;
             }));

             // Optional: Toast only if viewing? Or always.
             // data.room_id is string
             // selectedChat.id is string
             toast({
                 title: "Chat Cleared",
                 description: "The chat history has been cleared.",
             });
        });

        return () => {
             socket.off("new_message");
             socket.off("new_friend");
             socket.off("new_notification");
             socket.off("update_data");
             socket.off("added_to_room");
             socket.off("new_private_chat");
             socket.off("room_deleted");
             socket.off("chat_cleared");
             socket.off("user_status_change");
        }
  }, [socket, user]);

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

  // Join rooms when socket is ready and chatrooms fetched
  useEffect(() => {
      if (socket && chatrooms.length > 0) {
          chatrooms.forEach(room => {
              socket.emit("join_room", { room_id: room.id });
          });
      }
  }, [socket, chatrooms]); // chatrooms ref changes on setChatrooms

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
    // Determine userStatus if DM
    let userStatus = undefined;
    if (chatroom.otherUserId) {
        const friend = friends.find(f => f.id === chatroom.otherUserId);
        if (friend) {
            userStatus = { online: friend.online, lastSeen: friend.lastSeen };
        }
    }

    // Optimistically set selected chat
    setSelectedChat({ ...chatroom, userStatus });

    try {
        const res = await fetch(`${API_URL}/messages?room_id=${chatroom.id}`);
        if (res.ok) {
            const data = await res.json();
            const fullChatroom = {
                ...chatroom,
                messages: data.data,
                userStatus
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

  const handleRemoveFriend = async (friendId: string) => {
    if (!confirm("Are you sure you want to remove this friend?")) return;

    if (!user) return;

    try {
        const res = await fetch(`${API_URL}/friends/${friendId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: user.id
            }),
        });

        if (res.ok) {
            setFriends(prev => prev.filter(f => f.id !== friendId));
        } else {
            console.error("Failed to remove friend");
            alert("Failed to remove friend");
        }
    } catch (error) {
        console.error("Error removing friend:", error);
        alert("Error removing friend");
    }
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
    if (!selectedChat || !user) return;
    try {
        const res = await fetch(`${API_URL}/chatrooms/invite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                room_id: selectedChat.id,
                user_id: userId,
                sender_id: user.id
            })
        });
        if (!res.ok) {
            console.error("Failed to invite member");
            alert("Failed to invite member");
        } else {
            // Frontend updates are handled via socket events 'new_notification' to the invitee
            // The sender gets a success alert from the dialog component
        }
    } catch (error) {
        console.error("Error inviting member:", error);
    }
  };

  const handleSendMessage = (content: string, attachment?: { url: string, type: string, name: string }) => {
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
            content: content,
            attachment_url: attachment?.url,
            attachment_type: attachment?.type,
            original_name: attachment?.name
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
            socket={socket}
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
