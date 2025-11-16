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
};

export type Chatroom = {
  id: string;
  name: string;
  topic: string;
  messages: Message[];
};

export type Friend = User;

export const users: User[] = [
  { id: 'user-1', name: 'Sarah Lee', avatarUrl: 'https://picsum.photos/seed/sarah/40/40', online: true },
  { id: 'user-2', name: 'Mike Johnson', avatarUrl: 'https://picsum.photos/seed/mike/40/40', online: false },
  { id: 'user-3', name: 'Chloe Davis', avatarUrl: 'https://picsum.photos/seed/chloe/40/40', online: true },
  { id: 'user-4', name: 'David Chen', avatarUrl: 'https://picsum.photos/seed/david/40/40', online: false },
  { id: 'user-5', name: 'Emily Carter', avatarUrl: 'https://picsum.photos/seed/emily/40/40', online: true },
  { id: 'user-6', name: 'James Brown', avatarUrl: 'https://picsum.photos/seed/james/40/40', online: true },
  { id: 'user-7', name: 'Jessica Williams', avatarUrl: 'https://picsum.photos/seed/jessica/40/40', online: false },
  { id: 'user-8', name: 'Chris Miller', avatarUrl: 'https://picsum.photos/seed/chris/40/40', online: true },
  { id: 'user-9', name: 'Olivia Wilson', avatarUrl: 'https://picsum.photos/seed/olivia/40/40', online: false },
];

export const loggedInUser = users[4]; // Emily Carter is logged in

export const friends: Friend[] = [users[0], users[1], users[2]];

export const chatrooms: Chatroom[] = [
  {
    id: 'room-1',
    name: '#general',
    topic: 'General chatter and announcements',
    messages: [
      { id: 'msg-1-1', content: 'Hey everyone, welcome to Chitter Chatter!', sender: users[0], timestamp: '10:30 AM' },
      { id: 'msg-1-2', content: 'Glad to be here! The UI is looking great.', sender: users[2], timestamp: '10:31 AM' },
      { id: 'msg-1-3', content: 'What do you all think of the new color theme?', sender: loggedInUser, timestamp: '10:32 AM' },
      { id: 'msg-1-4', content: 'I love the soft blue, very calming.', sender: users[0], timestamp: '10:33 AM' },
    ],
  },
  {
    id: 'room-2',
    name: '#design-talk',
    topic: 'Discussing UI/UX trends',
    messages: [
      { id: 'msg-2-1', content: 'Has anyone seen the latest article on neumorphism?', sender: users[1], timestamp: '11:00 AM' },
      { id: 'msg-2-2', content: 'Yeah, I read it. Interesting take, but not sure about its practicality in complex interfaces. The accessibility concerns are real.', sender: users[2], timestamp: '11:02 AM' },
      { id: 'msg-2-3', content: 'Totally agree. It looks cool for a music player app, but for a data-heavy dashboard? Probably not.', sender: loggedInUser, timestamp: '11:05 AM' },
    ],
  },
  {
    id: 'room-3',
    name: '#project-phoenix',
    topic: 'Updates on the Phoenix project',
    messages: [
      { id: 'msg-3-1', content: 'Just pushed the latest updates to the staging branch.', sender: users[3], timestamp: 'Yesterday' },
      { id: 'msg-3-2', content: 'Thanks, David. I\'ll review them this afternoon.', sender: loggedInUser, timestamp: '9:05 AM' },
    ],
  },
  {
    id: 'room-4',
    name: '#random',
    topic: 'Anything and everything',
    messages: [],
  },
];
