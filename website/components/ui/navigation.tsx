'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useSession, signOut } from 'next-auth/react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { 
  MessageSquare, 
  Search, 
  Cloud, 
  HelpCircle, 
  Home,
  Menu,
  X,
  LogOut,
  User
} from 'lucide-react';

const navigation = [
  { name: 'Home', href: '/', icon: Home },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Query', href: '/query', icon: Search },
  { name: 'AWS Tools', href: '/aws', icon: Cloud },
  { name: 'Help', href: '/help', icon: HelpCircle },
];

export function Navigation() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();
  const { data: session } = useSession();

  return (
    <nav className="glassmorphism border-b border-green-500/20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 justify-between">
          <div className="flex">
            <div className="flex flex-shrink-0 items-center">
              <Link href="/" className="flex items-center space-x-2">
                <div className="h-8 w-8 rounded-full bg-gradient-to-r from-green-400 to-blue-500 cyber-glow" />
                <span className="neon-text-green text-xl font-bold terminal-font">
                  AWS.AI
                </span>
              </Link>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={`inline-flex items-center space-x-1 px-1 pt-1 text-sm font-medium transition-colors duration-200 ${
                      isActive
                        ? 'neon-text-green border-b-2 border-green-400'
                        : 'text-muted-foreground hover:text-green-400 hover:border-green-400/50 border-b-2 border-transparent'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.name}</span>
                  </Link>
                );
              })}
            </div>
          </div>

          <div className="hidden sm:ml-6 sm:flex sm:items-center">
            {session ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={session.user?.image || ''} alt={session.user?.name || ''} />
                      <AvatarFallback className="bg-green-500/20 text-green-400">
                        {session.user?.name?.[0] || session.user?.email?.[0] || 'U'}
                      </AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56 glassmorphism" align="end">
                  <DropdownMenuItem disabled>
                    <User className="mr-2 h-4 w-4" />
                    <span>{session.user?.email}</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => signOut()}>
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Sign out</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <Link href="/auth/signin">
                <Button variant="outline" className="cyber-glow">
                  Sign In
                </Button>
              </Link>
            )}
          </div>

          <div className="-mr-2 flex items-center sm:hidden">
            <Button
              variant="ghost"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-muted-foreground hover:text-green-400"
            >
              {mobileMenuOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <div className="sm:hidden">
          <div className="space-y-1 pb-3 pt-2">
            {navigation.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center space-x-3 px-3 py-2 text-base font-medium transition-colors duration-200 ${
                    isActive
                      ? 'neon-text-green bg-green-500/10 border-r-4 border-green-400'
                      : 'text-muted-foreground hover:text-green-400 hover:bg-green-500/5'
                  }`}
                  onClick={() => setMobileMenuOpen(false)}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </div>
          <div className="border-t border-green-500/20 pb-3 pt-4">
            <div className="px-4">
              {session ? (
                <div className="flex items-center space-x-3">
                  <Avatar className="h-10 w-10">
                    <AvatarImage src={session.user?.image || ''} alt={session.user?.name || ''} />
                    <AvatarFallback className="bg-green-500/20 text-green-400">
                      {session.user?.name?.[0] || session.user?.email?.[0] || 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-green-400">
                      {session.user?.name || session.user?.email}
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => signOut()}
                      className="h-auto p-0 text-xs text-muted-foreground hover:text-red-400"
                    >
                      Sign out
                    </Button>
                  </div>
                </div>
              ) : (
                <Link href="/auth/signin">
                  <Button variant="outline" className="w-full cyber-glow">
                    Sign In
                  </Button>
                </Link>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}