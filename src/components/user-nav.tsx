"use client";

import { LogOut, PlusCircle, Settings, User as UserIcon } from "lucide-react";
import { useRouter } from "next/navigation";

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

export function UserNav({ user }: UserNavProps) {
  const router = useRouter();

  const getInitials = (name: string) => {
    return name.split(' ').map(n => n[0]).join('');
  }

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
