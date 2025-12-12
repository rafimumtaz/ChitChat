export type User = {
  id: string;
  name: string;
  avatarUrl: string;
  online: boolean;
};

export type Message = {
  id: string;
  content: string;
  timestamp: string;
  sender: User;
  attachment_url?: string;
  attachment_type?: string;
  original_name?: string;
};

export type Chatroom = {
  id: string;
  name: string;
  topic: string;
  messages: Message[];
};

export type Friend = User;

// Keep types but clear data
export const users: User[] = [];
export const loggedInUser: User | null = null;
export const friends: Friend[] = [];
export const chatrooms: Chatroom[] = [];
