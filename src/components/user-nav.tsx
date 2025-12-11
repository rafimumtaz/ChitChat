"use client";

import { Bell, LogOut, PlusCircle, Settings, User as UserIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import io from "socket.io-client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { User } from "@/lib/data";
import { ThemeCustomizer } from "./theme-customizer";

interface UserNavProps {
  user: User;
}

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Check, X } from "lucide-react";

export function UserNav({ user }: UserNavProps) {
  const router = useRouter();
  const [notifications, setNotifications] = useState<any[]>([]);
  const [openNotifications, setOpenNotifications] = useState(false);

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('');
  }

  // Fetch notifications
  useEffect(() => {
      const fetchNotifications = async () => {
          const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
          try {
              const res = await fetch(`${API_URL}/notifications?user_id=${user.id}`);
              if (res.ok) {
                  const data = await res.json();
                  setNotifications(data.data);
              }
          } catch (error) {
              console.error("Error fetching notifications", error);
          }
      };

      fetchNotifications();

      // Listen for real-time notifications
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      const socket = io(API_URL);
      socket.emit("join_user_room", { user_id: user.id });

      socket.on("new_notification", (data: any) => {
          // data just has message, we need struct.
          // For simplicity, just refetch or mock append.
          // Since we need ID for actions, refetch is safer or we update backend to send full object.
          // Let's refetch for consistency.
          fetchNotifications();
      });

      return () => { socket.disconnect(); }
  }, [user.id]);

  const handleRespond = async (notifId: number, action: 'ACCEPT' | 'REJECT') => {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
      try {
          const res = await fetch(`${API_URL}/notifications/${notifId}/respond`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ action })
          });

          if (res.ok) {
              setNotifications(prev => prev.filter(n => n.notif_id !== notifId));
          }
      } catch (error) {
          console.error("Error responding to notification", error);
      }
  };

  const handleLogout = async () => {
    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';
    try {
        await fetch(`${API_URL}/logout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id })
        });
    } catch (error) {
        console.error("Logout failed:", error);
    }

    localStorage.removeItem("user");
    router.push("/login");
  }

  return (
    <div className="flex items-center gap-1">
      <ThemeCustomizer />
      <Dialog open={openNotifications} onOpenChange={setOpenNotifications}>
        <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                {notifications.length > 0 && (
                    <span className="absolute top-1 right-1 h-2.5 w-2.5 rounded-full bg-red-600" />
                )}
            </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
                <DialogTitle>Notifications</DialogTitle>
                <DialogDescription>Manage your friend requests and invites.</DialogDescription>
            </DialogHeader>
            <ScrollArea className="max-h-[300px] pr-4">
                <div className="space-y-4">
                    {notifications.length === 0 ? (
                        <p className="text-center text-muted-foreground py-4">No new notifications.</p>
                    ) : (
                        notifications.map((notif) => (
                            <div key={notif.notif_id} className="flex flex-col gap-2 p-3 border rounded-lg">
                                <p className="text-sm">
                                    <span className="font-semibold">{notif.sender_name}</span>
                                    {notif.type === 'FRIEND_REQUEST' ? ' sent you a friend request.' : ` invited you to ${notif.room_name}.`}
                                </p>
                                <div className="flex gap-2 justify-end">
                                    <Button size="sm" variant="outline" className="text-red-500 hover:text-red-600 hover:bg-red-50" onClick={() => handleRespond(notif.notif_id, 'REJECT')}>
                                        Reject
                                    </Button>
                                    <Button size="sm" onClick={() => handleRespond(notif.notif_id, 'ACCEPT')}>
                                        Accept
                                    </Button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </ScrollArea>
        </DialogContent>
      </Dialog>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="relative h-10 w-10 rounded-full">
            <Avatar className="h-10 w-10">
              <AvatarImage src={user.avatarUrl} alt={user.name} data-ai-hint="woman profile" />
              <AvatarFallback>{getInitials(user.name)}</AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end" forceMount>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">{user.name}</p>
              <p className="text-xs leading-none text-muted-foreground">
                {user.name.toLowerCase().replace(' ', '.')}@chitter.chatter
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem>
              <UserIcon className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <PlusCircle className="mr-2 h-4 w-4" />
              <span>New Team</span>
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            <span>Log out</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
