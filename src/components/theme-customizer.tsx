"use client";

import { Paintbrush } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useEffect, useState } from "react";

const colors = [
  { name: 'Default', primary: '217 100% 81%', accent: '246 100% 85%' },
  { name: 'Mint', primary: '158 90% 70%', accent: '178 80% 80%' },
  { name: 'Sakura', primary: '346 80% 85%', accent: '336 70% 90%' },
  { name: 'Sunset', primary: '24 95% 75%', accent: '45 90% 70%' },
  { name: 'Ocean', primary: '210 80% 70%', accent: '190 90% 65%' },
  { name: 'Lavender', primary: '250 70% 80%', accent: '260 80% 90%' },
];

export function ThemeCustomizer() {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const handleColorChange = (primary: string, accent: string) => {
    document.documentElement.style.setProperty('--primary', primary);
    document.documentElement.style.setProperty('--accent', accent);
  };

  if (!isMounted) {
    return (
        <div className="h-9 w-9 flex items-center justify-center animate-pulse rounded-md" />
    );
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon">
          <Paintbrush className="h-5 w-5" />
          <span className="sr-only">Customize Theme</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64" align="end">
        <div className="grid gap-4">
            <div className="space-y-2">
                <h4 className="font-medium leading-none">Customize UI</h4>
                <p className="text-sm text-muted-foreground">
                    Pick a color scheme for the app.
                </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
                {colors.map((color) => (
                    <Button
                        key={color.name}
                        variant="outline"
                        className="justify-start h-8 px-2"
                        onClick={() => handleColorChange(color.primary, color.accent)}
                    >
                        <div className="flex items-center gap-2">
                            <div className="h-4 w-4 rounded-full border" style={{ backgroundColor: `hsl(${color.primary})` }} />
                            <span className="text-xs">{color.name}</span>
                        </div>
                    </Button>
                ))}
            </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
